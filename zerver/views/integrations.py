from collections import OrderedDict
from django.views.generic import TemplateView
from django.conf import settings

from zerver.lib.integrations import INTEGRATIONS
from zerver.lib.utils import get_subdomain

class IntegrationView(TemplateView):
    template_name = 'zerver/integrations.html'

    def get_context_data(self, **kwargs):
        context = super(IntegrationView, self).get_context_data(**kwargs)
        alphabetical_sorted_integration = OrderedDict(sorted(INTEGRATIONS.items()))
        context['integrations_dict'] = alphabetical_sorted_integration
        subdomain = get_subdomain(self.request)
        if subdomain:
            settings_html = '<a href="/#settings">Zulip settings page</a>'
            subscriptions_html = '<a target="_blank" href="../#subscriptions">subscriptions page</a>'
            subdomain_ = subdomain
        else:
            settings_html = 'Zulip settings page'
            subscriptions_html = 'subscriptions page'
            subdomain_ = 'yourZulipDomain'

        external_api_path_subdomain = '%s.%s' % (subdomain_, settings.EXTERNAL_API_PATH)
        external_api_uri_subdomain = '%s%s' % (settings.EXTERNAL_URI_SCHEME,
                                               external_api_path_subdomain)

        context['settings_html'] = settings_html
        context['subscriptions_html'] = subscriptions_html
        context['external_api_path_subdomain'] = external_api_path_subdomain
        context['external_api_uri_subdomain'] = external_api_uri_subdomain

        return context
