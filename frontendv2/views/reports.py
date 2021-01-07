import operator
from functools import reduce
import datetime, calendar
import dateutil.parser

import json
from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q, Count, Max
from django.contrib import messages
from django.http import JsonResponse
from django import forms
from django.contrib.auth import authenticate, login as login_user, logout as logout_user
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.views import PasswordResetView as DjangoPasswordResetView

from corm.models import *
from corm.connectors import ConnectionManager

from frontendv2.views import SavannahView
from frontendv2.models import ManagerInvite
from frontendv2.views.charts import PieChart

class Reports(SavannahView):
    def __init__(self, request, community_id):
        super().__init__(request, community_id)
        self.active_tab = "reports"

    def all_reports(self):
        return Report.objects.filter(community=self.community).order_by('-generated')

    @login_required
    def as_view(request, community_id):
        view = Reports(request, community_id)
        if request.method == "POST":
            pass
        return render(request, "savannahv2/reports.html", view.context)

def view_report(request, community_id, report_id):
    report = get_object_or_404(Report, id=report_id)
    if report.report_type == Report.GROWTH:
        return GrowthReport.as_view(request, community_id, report)
    elif report.report_type == Report.ANNUAL:
        return AnnualReport.as_view(request, community_id, report)
    else:
        messages.error(request, "Unknown report type: %s" % self.report.report_type)
        return redirect('reports', community_id=community_id)

class GrowthReport(SavannahView):
    def __init__(self, request, community_id, report):
        super().__init__(request, community_id)
        self.active_tab = "reports"
        self.report = report
        self.data = json.loads(self.report.data)
        try:
            self.previous = Report.objects.filter(community=self.community, report_type=Report.GROWTH, generated__lt=report.generated).order_by('-generated')[0]
            self.previous_data = json.loads(self.previous.data)
        except:
            self.previous = None
            self.previous_data = None

    @property
    def month_name(self):
        return calendar.month_name[self.report.generated.month]
        
    @property
    def previous_month_name(self):
        if self.previous is None:
            return "Previous"
        return calendar.month_name[self.previous.generated.month]
        
    @property
    def new_member_count(self):
        return len(self.data['new_members'])

    @property 
    def new_member_diff(self):
        if self.previous is None:
            return 0
        if len(self.previous_data['new_members']) == 0:
            return 0
        diff = len(self.data['new_members']) - len(self.previous_data['new_members'])
        return 100 * diff / len(self.previous_data['new_members'])

    @property
    def new_contributor_count(self):
        return len(self.data['new_contributors'])
        
    @property 
    def new_contributor_diff(self):
        if self.previous is None:
            return 0
        if len(self.previous_data['new_contributors']) == 0:
            return 0
        diff = len(self.data['new_contributors']) - len(self.previous_data['new_contributors'])
        return 100 * diff / len(self.previous_data['new_contributors'])

    @property
    def new_members(self):
        for member in self.data['new_members']:
            member['joined'] = dateutil.parser.parse(member["joined"])
            yield(member)

    @property
    def new_contributors(self):
        for member in self.data['new_contributors']:
            member['first_contrib'] = dateutil.parser.parse(member["first_contrib"])
            yield(member)

    @property
    def top_contributors(self):
        for member in self.data['top_contributors']:
            yield(member)

    @property
    def top_supporters(self):
        for member in self.data['top_supporters']:
            yield(member)

    @property
    def members_chart_keys(self):
        activity = self.data['member_activity']
        return activity['days']

    @property
    def members_chart_counts(self):
        activity = self.data['member_activity']
        return activity['joined']

    @property
    def members_chart_active(self):
        activity = self.data['member_activity']
        return activity['active']

    @property
    def members_previous_counts(self):
        if self.previous is None:
            return []
        activity = self.previous_data['member_activity']
        return activity['joined']

    @property
    def members_previous_active(self):
        if self.previous is None:
            return []
        activity = self.previous_data['member_activity']
        return activity['active']

    @login_required
    def as_view(request, community_id, report):
        view = GrowthReport(request, community_id, report)
        if request.method == "POST":
            pass
        return render(request, "savannahv2/report_growth.html", view.context)

class AnnualReport(SavannahView):
    def __init__(self, request, community_id, report):
        super().__init__(request, community_id)
        self.active_tab = "reports"
        self.report = report
        self.data = json.loads(self.report.data)
        self.charts = set()

    @property
    def year_name(self):
        return self.data['start'].year
        
    @property
    def new_member_count(self):
        return self.data['counts']['new_members']

    @property
    def new_contributor_count(self):
        return self.data['counts']['new_contributors']

    @property
    def conversation_count(self):
        return self.data['counts']['conversations']

    @property
    def contribution_count(self):
        return self.data['counts']['contributions']

    @property
    def top_contributors(self):
        for member in self.data['top_contributors']:
            yield(member)

    @property
    def top_supporters(self):
        for member in self.data['top_supporters']:
            yield(member)

    @property
    def members_chart_keys(self):
        activity = self.data['member_activity']
        return activity['months']

    @property
    def members_chart_joined(self):
        activity = self.data['member_activity']
        return activity['joined']

    @property
    def members_chart_active(self):
        activity = self.data['member_activity']
        return activity['active']

    @property
    def conversation_sources_chart(self):
        chart = PieChart("conversationSources", title="Conversations by Source")
        for source in self.data['conversation_sources']:
                chart.add(ConnectionManager.display_name(source['connector']), source['conversation_count'])
        self.charts.add(chart)
        return chart

    @property
    def contribution_types_chart(self):
        chart = PieChart("conversationSources", title="Contributions by Type")
        for t in self.data['contribution_types']:
                chart.add("%s in %s" % (t['name'], t['source_name']), t['contribution_count'])
        self.charts.add(chart)
        return chart

    @property
    def contribution_types(self):
        return self.data['contribution_types']

    @login_required
    def as_view(request, community_id, report):
        view = AnnualReport(request, community_id, report)
        if request.method == "POST":
            pass
        return render(request, "savannahv2/report_annual.html", view.context)
