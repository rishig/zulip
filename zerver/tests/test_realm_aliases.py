# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from zerver.lib.actions import do_create_realm, do_change_realm_alias
from zerver.lib.domains import validate_domain
from zerver.lib.test_classes import ZulipTestCase
from zerver.models import get_realm, get_realm_by_email_domain, \
    GetRealmByDomainException, RealmAlias
from zerver.models import get_realm, get_realm_by_email_domain, \
    email_allowed_for_realm, GetRealmByDomainException, RealmAlias
import ujson


class RealmAliasTest(ZulipTestCase):
    def test_list(self):
        # type: () -> None
        self.login("iago@zulip.com")
        realm = get_realm('zulip')
        alias = RealmAlias(realm=realm, domain='zulip.org', subdomains_allowed=False)
        alias.save()
        result = self.client_get("/json/realm/domains")
        self.assert_json_success(result)
        self.assertEqual(200, result.status_code)
        content = ujson.loads(result.content)
        self.assertEqual(len(content['domains']), 2)

    def test_not_realm_admin(self):
        # type: () -> None
        self.login("hamlet@zulip.com")
        result = self.client_post("/json/realm/domains")
        self.assert_json_error(result, 'Must be a realm administrator')
        result = self.client_delete("/json/realm/domains/15")
        self.assert_json_error(result, 'Must be a realm administrator')

    def test_create(self):
        # type: () -> None
        self.login("iago@zulip.com")
        data = {
            'domain': ujson.dumps(''),
            'subdomains_allowed': ujson.dumps(False),
        }
        result = self.client_post("/json/realm/domains", info=data)
        self.assert_json_error(result, "Invalid domain: Domain can't be empty.")

        data['domain'] = ujson.dumps('zulip.org')
        result = self.client_post("/json/realm/domains", info=data)
        self.assert_json_success(result)

        result = self.client_post("/json/realm/domains", info=data)
        self.assert_json_error(result, "The domain zulip.org is already a part of your organization.")

    def test_patch(self):
        # type: () -> None
        self.login("iago@zulip.com")
        realm = get_realm('zulip')
        alias = RealmAlias.objects.create(realm=realm, domain='zulip.org',
                                          subdomains_allowed=False)
        data = {
            'subdomains_allowed': ujson.dumps(True),
        }
        url = "/json/realm/domains/{}".format(alias.id)
        result = self.client_patch(url, data)
        self.assert_json_success(result)

        url = "/json/realm/domains/-1"
        result = self.client_patch(url, data)
        self.assertEqual(result.status_code, 404)

    def test_delete(self):
        # type: () -> None
        self.login("iago@zulip.com")
        realm = get_realm('zulip')
        alias_id = RealmAlias.objects.create(realm=realm, domain='zulip.org').id
        aliases_count = RealmAlias.objects.count()
        result = self.client_delete("/json/realm/domains/{0}".format(alias_id + 1))
        self.assert_json_error(result, 'No such entry found.')

        result = self.client_delete("/json/realm/domains/{0}".format(alias_id))
        self.assert_json_success(result)
        self.assertEqual(RealmAlias.objects.count(), aliases_count - 1)

    def test_get_realm_by_email_domain(self):
        # type: () -> None
        realm1, created = do_create_realm('testrealm1', 'Test Realm 1')
        realm2, created = do_create_realm('testrealm2', 'Test Realm 2')

        alias = RealmAlias.objects.create(realm=realm1, domain='test.com', subdomains_allowed=False)
        RealmAlias.objects.create(realm=realm2, domain='test1.test.com', subdomains_allowed=True)

        self.assertEqual(get_realm_by_email_domain('user@zulip.com').string_id, 'zulip')
        self.assertEqual(get_realm_by_email_domain('user@fakedomain.com'), None)
        self.assertEqual(get_realm_by_email_domain('user@test.com').string_id, 'testrealm1')
        self.assertEqual(get_realm_by_email_domain('user@test1.test.com').string_id, 'testrealm2')
        self.assertEqual(get_realm_by_email_domain('user@test2.test.com'), None)
        self.assertEqual(get_realm_by_email_domain('user@test2.test1.test.com').string_id, 'testrealm2')

        do_change_realm_alias(alias, True)
        self.assertEqual(get_realm_by_email_domain('user@test2.test.com').string_id, 'testrealm1')
        self.assertEqual(get_realm_by_email_domain('user@test3.test2.test.com').string_id, 'testrealm1')

        with self.settings(REALMS_HAVE_SUBDOMAINS = True), self.assertRaises(GetRealmByDomainException):
            get_realm_by_email_domain('user@zulip.com')

    def test_email_allowed_for_realm(self):
        # type: () -> None
        realm1, created = do_create_realm('testrealm1', 'Test Realm 1', restricted_to_domain=True)
        realm2, created = do_create_realm('testrealm2', 'Test Realm 2', restricted_to_domain=True)

        alias = RealmAlias.objects.create(realm=realm1, domain='test.com', subdomains_allowed=False)
        RealmAlias.objects.create(realm=realm2, domain='test1.test.com', subdomains_allowed=True)

        self.assertEqual(email_allowed_for_realm('user@test.com', realm1), True)
        self.assertEqual(email_allowed_for_realm('user@test1.test.com', realm1), False)
        self.assertEqual(email_allowed_for_realm('user@test1.test.com', realm2), True)
        self.assertEqual(email_allowed_for_realm('user@test2.test1.test.com', realm2), True)
        self.assertEqual(email_allowed_for_realm('user@test2.test.com', realm2), False)

        do_change_realm_alias(alias, True)
        self.assertEqual(email_allowed_for_realm('user@test.com', realm1), True)
        self.assertEqual(email_allowed_for_realm('user@test1.test.com', realm1), True)
        self.assertEqual(email_allowed_for_realm('user@test1.com', realm1), False)

    def test_realm_aliases_uniqueness(self):
        # type: () -> None
        realm = get_realm('zulip')
        with self.settings(REALMS_HAVE_SUBDOMAINS=True), self.assertRaises(IntegrityError):
            RealmAlias.objects.create(realm=realm, domain='zulip.com', subdomains_allowed=True)

    def test_validate_domain(self):
        # type: () -> None
        invalid_domains = ['', 'test', 't.', 'test.', '.com', '-test', 'test...com',
                           'test-', 'test_domain.com', 'test.-domain.com']
        for domain in invalid_domains:
            with self.assertRaises(ValidationError):
                validate_domain(domain)
