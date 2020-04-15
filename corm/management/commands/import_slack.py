from django.core.management.base import BaseCommand, CommandError
import datetime
import re
from perceval.backends.core.slack import Slack
from corm.models import Community, Source, Member, Contact, Channel, Conversation

class Command(BaseCommand):
    help = 'Import data from Slack sources'

    def handle(self, *args, **options):
      print("Importing Slack data")

      for source in Source.objects.filter(connector="corm.plugins.slack"):
        print("From %s:" % source.name)
        for channel in source.channel_set.all():
          print("  %s" % channel.name)
          if channel.origin_id and source.auth_secret:
            import_slack(channel)
        source.last_import = datetime.datetime.utcnow()
        source.save()

def import_slack(channel):
  source = channel.source
  community = source.community
  slack = Slack(channel.origin_id, channel.source.auth_secret)
  items = [i for i in slack.fetch(from_date=channel.source.last_import)]
  for slack_id, user in slack._users.items():
      if not user.get('is_bot'):
        slack_user_id = "slack.com/%s" % slack_id
        contact_matches = Contact.objects.filter(origin_id=slack_user_id, source=source)
        if contact_matches.count() == 0:
          member = Member.objects.create(community=community, name=user.get('real_name'))
          Contact.objects.get_or_create(origin_id=slack_user_id, defaults={'member':member, 'source':source, 'detail':user.get('name')})

  tag_matcher = re.compile('\<\@([^>]+)\>')
  for item in items:
    if item.get('data').get('subtype') is None and item.get('data').get('user_data'):
      tagged = set(tag_matcher.findall(item.get('data').get('text')))

      # We only want to check comments that tag somebody else, or are part of a thread
      if len(tagged) > 0 or 'thread_ts' in item.get('data'):
        #print("Importing conversation from %s" % item.get('data').get('user_data').get('name'))
        slack_user_id = "slack.com/%s" % item.get('data').get('user_data').get('id')
        contact = Contact.objects.get(origin_id=slack_user_id)
        tstamp = datetime.datetime.fromtimestamp(float(item.get('data').get('ts')))
        slack_convo_id = "slack.com/conversation/%s" % item.get('data').get('client_msg_id')
        server = source.server or "slack.com"
        slack_convo_link = "https://%s/archives/%s/p%s" % (server, channel.origin_id, item.get('data').get('ts').replace(".", ""))
        thread = None
        if 'thread_ts' in item.get('data'):
          slack_convo_link = slack_convo_link + "?thread_ts=%s&cid=%s" % (item.get('data').get('thread_ts'), channel.origin_id)
          slack_thread_link = "https://%s/archives/%s/p%s" % (server, channel.origin_id, item.get('data').get('thread_ts').replace(".", ""))
          slack_thread_link = slack_thread_link + "?thread_ts=%s&cid=%s" % (item.get('data').get('thread_ts'), channel.origin_id)
          thread_tstamp = datetime.datetime.fromtimestamp(float(item.get('data').get('ts')))
          thread, created = Conversation.objects.get_or_create(origin_id=slack_thread_link, defaults={'channel':channel, 'timestamp':thread_tstamp, 'location': slack_thread_link})
          thread.participants.add(contact.member)

        convo_text = item.get('data').get('text')
        for tagged_user in tagged:
          if slack._users.get(tagged_user):
              convo_text = convo_text.replace("<@%s>"%tagged_user, "@%s"%slack._users.get(tagged_user).get('real_name'))
        convo_text = item.get('data').get('user_data').get('real_name') + ": " + convo_text
        try:
          convo, created = Conversation.objects.update_or_create(origin_id=slack_convo_link, defaults={'channel':channel, 'content':convo_text, 'timestamp':tstamp, 'location':slack_convo_link})
        except:
          import pdb; pdb.set_trace()
        convo.participants.add(contact.member)

        for tagged_user in tagged:
          #if not slack._users.get(tagged_user):
            #print("Unknown Slack user: %s" % tagged_user)
            #continue
          #print("Checking for %s" % tagged_user)
          try:
            tagged_user_id = "slack.com/%s" % tagged_user
            tagged_contact = Contact.objects.get(origin_id=tagged_user_id)
            convo.participants.add(tagged_contact.member)
            if thread is not None:
              thread.participants.add(tagged_contact.member)
            contact.member.add_connection(tagged_contact.member, source, tstamp)
          except:
            print("    Failed to find Contact for %s" % tagged_user)

        # Connect this conversation's speaker to everyone else in this thread
        if thread is not None:
          for thread_member in thread.participants.all():
            try:
              contact.member.add_connection(thread_member, source, tstamp)
              convo.participants.add(thread_member)
            except Exception as e:
              print("    Failed to make connection between %s and %s" % (contact.member, tagged_contact.member))
              print(e)
