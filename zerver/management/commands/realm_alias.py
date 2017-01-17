from __future__ import absolute_import
from __future__ import print_function

from typing import Any

from argparse import ArgumentParser
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError
from zerver.models import Realm, RealmAlias, get_realm, can_add_alias
from zerver.lib.actions import get_realm_aliases, do_add_realm_alias, \
    do_change_realm_alias, do_remove_realm_alias
from zerver.lib.domains import validate_domain
import sys

class Command(BaseCommand):
    help = """Manage aliases for the specified realm"""

    def add_arguments(self, parser):
        # type: (ArgumentParser) -> None
        parser.add_argument('-r', '--realm',
                            dest='string_id',
                            type=str,
                            required=True,
                            help='The subdomain or string_id of the realm.')
        parser.add_argument('--op',
                            dest='op',
                            type=str,
                            default="show",
                            help='What operation to do (add, show, remove).')
        parser.add_argument('--allow-subdomains',
                            dest='allow_subdomains',
                            action="store_true",
                            default=False,
                            help='Whether subdomains are allowed or not.')
        parser.add_argument('alias', metavar='<alias>', type=str, nargs='?',
                            help="alias to add or remove")

    def handle(self, *args, **options):
        # type: (*Any, **str) -> None
        realm = get_realm(options["string_id"])
        if options["op"] == "show":
            print("Aliases for %s:" % (realm.domain,))
            for alias in get_realm_aliases(realm):
                if alias["subdomains_allowed"]:
                    print(alias["domain"] + " (subdomains allowed)")
                else:
                    print(alias["domain"] + " (subdomains not allowed)")
            sys.exit(0)

        domain = options['alias'].strip().lower()
        if options["op"] == "add":
            validate_domain(domain)
            if RealmAlias.objects.filter(realm=realm, domain=domain).exists():
                raise ValidationError("The domain %s is already a part of your organization." % (domain,))
            if not can_add_alias(domain):
                raise ValidationError("The domain %s belongs to another organization." % (domain,))
            alias = do_add_realm_alias(realm, domain, bool(options["allow_subdomains"]))
        elif options["op"] == "remove":
            try:
                RealmAlias.objects.get(realm=realm, domain=domain).delete()
                sys.exit(0)
            except RealmAlias.DoesNotExist:
                print("No such entry found!")
                sys.exit(1)
        else:
            self.print_help("./manage.py", "realm_alias")
            sys.exit(1)
