from collections import OrderedDict
from django.views.generic import TemplateView
from django.conf import settings

from zerver.lib.integrations import INTEGRATIONS

# TODO: write this properly, and put it somewhere reusable
def host_is_realm_uri(host):
    if host.split(':')[0] in ('zulipchat.com', 'localhost', 'zulipdev.com'):
        return False
    return True

# TODO also do this properly
def get_realm_from_host(host):
    return host.split('.')[0]

class IntegrationView(TemplateView):
    template_name = 'zerver/integrations.html'

    def get_context_data(self, **kwargs):
        context = super(IntegrationView, self).get_context_data(**kwargs)
        alphabetical_sorted_integration = OrderedDict(sorted(INTEGRATIONS.items()))
        context['integrations_dict'] = alphabetical_sorted_integration
        host = self.request.get_host()
        if host_is_realm_uri(host):
            settings_html = '<a href="/#settings">Zulip settings page</a>'
            subscriptions_html = '<a target="_blank" href="../#subscriptions">subscriptions page</a>'
            realm_str = get_realm_from_host(host)
        else:
            settings_html = 'Zulip settings page'
            subscriptions_html = 'subscriptions page'
            realm_str = 'yourZulipDomain'

        external_api_path_subdomain = '%s.%s' % (realm_str, settings.EXTERNAL_API_PATH)
        external_api_uri_subdomain = '%s%s' % (settings.EXTERNAL_URI_SCHEME,
                                               external_api_path_subdomain)

        context['settings_html'] = settings_html
        context['subscriptions_html'] = subscriptions_html
        context['external_api_path_subdomain'] = external_api_path_subdomain
        context['external_api_uri_subdomain'] = external_api_uri_subdomain

        return context
