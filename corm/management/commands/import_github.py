from django.core.management.base import BaseCommand, CommandError
import datetime
import re
import subprocess
import requests
from perceval.backends.core.github import GitHub, CATEGORY_PULL_REQUEST, CATEGORY_ISSUE
from corm.models import Community, Source, Member, Contact, Channel, Conversation

GITHUB_ISSUES_URL = 'https://api.github.com/repos/%(owner)s/%(repo)s/issues?state=all&since=%(since)s&page=%(page)s'
GITHUB_REVIEWS_URL = 'https://api.github.com/repos/%(owner)s/%(repo)s/pulls/%(pull_number)s/reviews'
GITHUB_TIMESTAMP = '%Y-%m-%dT%H:%M:%SZ'

class Command(BaseCommand):
    help = 'Import data from Github sources'
    API_TOKEN = None

    def handle(self, *args, **options):
      print("Importing Github data")

      for source in Source.objects.filter(connector="corm.plugins.github", auth_secret__isnull=False):
        print("From %s:" % source.name)
        self.API_TOKEN = source.auth_secret
        for channel in source.channel_set.all():
          print("  %s" % channel.name)
          if channel.origin_id and source.auth_secret:
            self.import_github(channel)
        source.last_import = datetime.datetime.utcnow()
        source.save()

    def api_request(self, url):
      #print("API Call: %s" % url)
      headers = {'Authorization': 'token %s' % self.API_TOKEN}
      return requests.get(url, headers=headers)

    def import_github(self, channel):
      source = channel.source
      community = source.community
      github_path = channel.origin_id.split('/')

      owner = github_path[3]
      repo = github_path[4]
      from_date = channel.source.last_import.strftime(GITHUB_TIMESTAMP)
      print("  since %s" % from_date)

      tag_matcher = re.compile('\@([a-zA-Z0-9]+)')
      found_members = dict()

      issues_page = 1
      while (issues_page):
        repo_issues_url = GITHUB_ISSUES_URL % {'owner': owner, 'repo': repo, 'since': from_date, 'page': issues_page}
            
        resp = self.api_request(repo_issues_url)
        if resp.status_code == 200:
            issues = resp.json()
            for issue in issues:

                participants = set()
                conversations = set()
                tstamp = datetime.datetime.strptime(issue['created_at'], GITHUB_TIMESTAMP)
                if issue.get('comments', 0) > 0:
                    github_convo_link = issue['url']
                    convo, created = Conversation.objects.update_or_create(origin_id=github_convo_link, defaults={'channel':channel, 'content':issue['body'], 'timestamp':tstamp, 'location':issue['html_url']})
                    conversations.add(convo)

                    if issue['user']['login'] in found_members:
                        member = found_members[issue['user']['login']]
                    else:
                        github_user_id = 'github.com/%s' % issue['user']['login']
                        contact_matches = Contact.objects.filter(origin_id=github_user_id, source=source)
                        if contact_matches.count() == 0:
                            member = Member.objects.create(community=community, name=issue['user']['login'], date_added=tstamp)
                            contact, created = Contact.objects.get_or_create(origin_id=github_user_id, defaults={'member':member, 'source':source, 'detail':issue['user']['login']})
                        else:
                            contact = contact_matches[0]
                            member = contact.member
                        found_members[issue['user']['login']] = member
                    participants.add(member)

                    comment_resp = self.api_request(issue['comments_url'])
                    if comment_resp.status_code == 200:
                        comments = comment_resp.json()
                        for comment in comments:
                            comment_tstamp = datetime.datetime.strptime(comment['created_at'], GITHUB_TIMESTAMP)
                            comment_convo, created = Conversation.objects.update_or_create(origin_id=comment['url'], defaults={'channel':channel, 'content':comment['body'], 'timestamp':tstamp, 'location':comment['html_url']})
                            if comment['user']['login'] in found_members:
                                comment_member = found_members[comment['user']['login']]
                            else:
                                comment_user_id = 'github.com/%s' % comment['user']['login']
                                contact_matches = Contact.objects.filter(origin_id=comment_user_id, source=source)
                                if contact_matches.count() == 0:
                                    comment_member = Member.objects.create(community=community, name=comment['user']['login'], date_added=comment_tstamp)
                                    Contact.objects.get_or_create(origin_id=comment_user_id, defaults={'member':comment_member, 'source':source, 'detail':comment['user']['login']})
                                else:
                                    comment_member = contact.member
                            participants.add(comment_member)
                            conversations.add(comment_convo)
                            tagged = set(tag_matcher.findall(comment['body']))
                            if tagged:
                                for tagged_user in tagged:
                                    if tagged_user in found_members:
                                        participants.add(found_members[tagged_user])
                                    else:
                                        try:
                                            tagged_user_id = "github.com/%s" % tagged_user
                                            tagged_contact = Contact.objects.get(origin_id=tagged_user_id)
                                            participants.add(tagged_contact.member)
                                        except:
                                            pass#print("    Failed to find Contact for %s" % tagged_user)


                tagged = set(tag_matcher.findall(issue['body']))
                if tagged:
                    for tagged_user in tagged:
                        if tagged_user in found_members:
                            participants.add(found_members[tagged_user])
                        else:
                            try:
                                tagged_user_id = "github.com/%s" % tagged_user
                                tagged_contact = Contact.objects.get(origin_id=tagged_user_id)
                                participants.add(tagged_contact.member)
                            except:
                                pass#print("    Failed to find Contact for %s" % tagged_user)


                # Add everybody involved as a participant in every conversation
                for convo in conversations:
                    convo.participants.set(participants)

                # Connect all participants
                for from_member in participants:
                    for to_member in participants:
                        if from_member.id != to_member.id:
                            from_member.add_connection(to_member, source, tstamp)


        # If there are more pages of issues, continue on to the next apge
        if 'link' in resp.headers and 'rel="next"' in resp.headers['link']:
            issues_page+= 1
        else:
            break