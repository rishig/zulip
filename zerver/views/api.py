from django.views.generic import TemplateView
from django.conf import settings

from zerver.lib.utils import get_subdomain

class APIView(TemplateView):
    template_name = 'zerver/api.html'

    def get_context_data(self, **kwargs):
        context = super(APIView, self).get_context_data(**kwargs)
        subdomain = get_subdomain(self.request)
        subdomain_ = subdomain if subdomain else 'yourZulipDomain'

        external_api_path_subdomain = '%s.%s' % (subdomain_, settings.EXTERNAL_API_PATH)
        external_api_uri_subdomain = '%s%s' % (settings.EXTERNAL_URI_SCHEME,
                                               external_api_path_subdomain)

        context['external_api_path_subdomain'] = external_api_path_subdomain
        context['external_api_uri_subdomain'] = external_api_uri_subdomain

        return context
