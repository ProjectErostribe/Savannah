import datetime
import re
import requests
from xml.etree import ElementTree as XMLParser
from html.parser import HTMLParser
import io
import pytz

from django.contrib import messages
from django import forms
from django.shortcuts import redirect, get_object_or_404, reverse, render
from django.urls import path

from corm.plugins import BasePlugin, PluginImporter
from corm.models import Community, Source, ContributionType, Contribution
from frontendv2.views import SavannahView

class RssLinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rss_links = dict()

    def handle_starttag(self, tag, attrs):
        #<link rel="alternate" type="application/rss+xml" title="InfluxData &raquo; Feed" href="https://www.influxdata.com/feed/" />
        if tag == 'link':
            link = dict()
            for key, value in attrs:
                link[key] = value
            if 'type' in link and link['type'] == "application/rss+xml":
                self.rss_links[link['href']] = link['title']

class RssForm(forms.ModelForm):
    class Meta:
        model = Source
        fields = ['name', 'server']
        labels = {
            'server': 'Website URL',
        }
    def __init__(self, *args, **kwargs):
        super(RssForm, self).__init__(*args, **kwargs)
        self.fields['server'].required = True

class SourceAdd(SavannahView):
    def _add_sources_message(self):
        pass

    def as_view(request):
        view = SourceAdd(request, community_id=request.session['community'])
        new_source = Source(community=view.community, connector="corm.plugins.rss", icon_name="fas fa-globe")
        if request.method == "POST":
            form = RssForm(data=request.POST, instance=new_source)
            if form.is_valid():
                # TODO: attempt API call to validate
                source = form.save()
                return redirect('channels', community_id=view.community.id, source_id=source.id)

        form = RssForm(instance=new_source)
        context = view.context
        context.update({
            'source_form': form,
            'source_plugin': 'Blog',
            'submit_text': 'Add',
            'submit_class': 'btn btn-success',
        })
        return render(request, 'savannahv2/source_add.html', context)

urlpatterns = [
    path('auth', SourceAdd.as_view, name='rss_auth'),
]

class RssPlugin(BasePlugin):

    def get_source_type_name(self):
        return "RSS"

    def get_import_command_name(self):
        return "rss"

    def get_source_importer(self, source):
        return RssImporter(source)

    def get_channels(self, source):
        channels = []

        resp = requests.get(source.server)   
        if resp.status_code == 200:
            data = resp.text
            try:
                rawxml = io.StringIO(data)
                tree = XMLParser.parse(rawxml)
                i = 0
                for feedchannel in tree.findall('channel'):
                    feed_url = feedchannel.find('{http://www.w3.org/2005/Atom}link').get('href')
                    channels.append({
                        'id': source.server,
                        'name': feedchannel.find('title').text.strip(),
                        'topic': feedchannel.find('description').text,
                        'count': i,
                    })
                    i += 1
                if len(channels) == 0:
                    raise Exception("No channels found in %s" % source.server)
            except:
                parser = RssLinkParser()
                parser.feed(data)
                i = 0
                for url, title in parser.rss_links.items():
                    if url.startswith('/'):
                        url = source.server + url
                    channels.append({
                        'id': url,
                        'name': title,
                        'topic': "",
                        'count': i,
                    })
                    i += 1
                if len(channels) == 0:
                    raise Exception("No RSS links found at %s" % source.server)
        else:
            print("Request failed: %s" % resp.content)
            raise Exception("Request failed: %s" % resp.content)
        return channels

class RssImporter(PluginImporter):

    def __init__(self, source):
        super().__init__(source)
        self.TIMESTAMP_FORMAT = '%a, %d %b %Y %H:%M:%S %z'
        self.BLOG_CONTRIBUTION, created = ContributionType.objects.get_or_create(community=source.community, source=source, name="Blog Post")

    def get_channels(self):
        channels = self.source.channel_set.filter(origin_id__isnull=False).order_by('last_import')
        return channels

    def import_channel(self, channel):
      source = channel.source
      community = source.community

      resp = requests.get(channel.origin_id)
      if resp.status_code == 200:
          rawxml = io.StringIO(resp.text)
          tree = XMLParser.parse(rawxml)
          for feedchannel in tree.findall('channel'):
              for item in feedchannel.findall('item'):
                self.import_item(item, channel, source, community)
          for item in tree.findall('item'):
            self.import_item(item, channel, source, community)

    def import_item(self, item, channel, source, community):
        article_link = item.find('link').text
        guid_node = item.find('guid')
        author_node = item.find('{http://purl.org/dc/elements/1.1/}creator')
        if author_node is None:
            author_node = item.find('author')
        if author_node is None or not hasattr(author_node, 'text'):
            return
        author_name = author_node.text
        if author_name is None:
            print("No author name for article: %s" % article_link)
            return
        tstamp = self.strptime(item.find('pubDate').text.strip()).replace(tzinfo=None)
        article_title = item.find('title').text.strip()
        if len(article_title) > 198:
            article_title = article_title[:198]
        origin_id = article_link
        blog_author_id = '%s/%s' % (source.server, author_name)
        member = self.make_member(blog_author_id, detail=author_name, channel=channel, tstamp=tstamp, name=author_name, speaker=True)

        blog_content = item.find('description').text
        origin_parts = origin_id.split("#")

        if len(origin_parts) == 2:
            if self.verbosity >= 2:
                print("Found comment: %s" % origin_id)
            if article_title.startswith("Comment on "):
                # Wordpress comments prefix this to the article title
                article_title = article_title[11:]
            contrib, created = Contribution.objects.get_or_create(community=community, origin_id=origin_parts[0], contribution_type=self.BLOG_CONTRIBUTION, defaults={'channel':channel, 'title':article_title, 'author':None, 'timestamp':tstamp, 'location':origin_parts[0]})
            convo = self.make_conversation(origin_id=origin_id, channel=channel, speaker=member, content=blog_content, tstamp=tstamp, location=origin_id, thread=contrib.conversation)
        else:
            if self.verbosity >= 2:
                print("Found article: %s" % origin_id)
            convo = self.make_conversation(origin_id=origin_id, channel=channel, speaker=member, content=blog_content, tstamp=tstamp, location=origin_id)
            contrib, created = Contribution.objects.update_or_create(community=community, origin_id=origin_id, contribution_type=self.BLOG_CONTRIBUTION, defaults={'channel':channel, 'title':article_title, 'author':member, 'timestamp':tstamp, 'title':article_title, 'location':article_link, 'conversation':convo})
            if channel.tag:
                contrib.tags.add(channel.tag)
