var common = require('../casper_lib/common.js').common;

var email = 'alice@test.example.com';
var domain = 'test.example.com';
var subdomain = 'testsubdomain';
var organization_name = 'Awesome Organization';
var REALMS_HAVE_SUBDOMAINS = casper.cli.get('subdomains');
var host;
var realm_host;

if (REALMS_HAVE_SUBDOMAINS) {
    host = 'zulipdev.com:9981';
    realm_host = subdomain + '.' + host;
} else {
    host = realm_host = 'localhost:9981';
}

casper.start('http://' + host + '/create_realm/');

casper.then(function () {
    // Submit the email for realm creation
    this.waitForSelector('form[action^="/create_realm/"]', function () {
        this.fill('form[action^="/create_realm/"]', {
            email: email
        }, true);
    });
    // Make sure confirmation email is send
    this.waitWhileSelector('form[action^="/create_realm/"]', function () {
         var regex = new RegExp('^http:\/\/[^\/]+\/accounts\/send_confirm\/' + email);
         this.test.assertUrlMatch(regex, 'Confirmation mail send');
    });
});

// Special endpoint enabled only during tests for extracting confirmation key
casper.thenOpen('http://' + host + '/confirmation_key/');

// Open the confirmation URL
casper.then(function () {
    var confirmation_key = JSON.parse(this.getPageContent()).confirmation_key;
    var confirmation_url = 'http://' + host + '/accounts/do_confirm/' + confirmation_key;
    this.thenOpen(confirmation_url);
});

// Make sure the realm creation page is loaded correctly
casper.then(function () {
    this.waitForSelector('.pitch', function () {
        this.test.assertSelectorHasText('.pitch', "You're almost there. We just need you to do one last thing.");
    });

    this.waitForSelector('.controls.fakecontrol', function () {
        this.test.assertSelectorHasText('.controls.fakecontrol', email);
    });

    this.waitForSelector('label[for=id_team_name]', function () {
        this.test.assertSelectorHasText('label[for=id_team_name]', 'Organization name');
    });
});

casper.then(function () {
    this.waitForSelector('form[action^="/accounts/register/"]', function () {
        if (REALMS_HAVE_SUBDOMAINS) {
            this.fill('form[action^="/accounts/register/"]', {
                full_name: 'Alice',
                realm_name: organization_name,
                realm_subdomain: subdomain,
                password: 'password',
                terms: true
            }, true);
        } else {
            this.fill('form[action^="/accounts/register/"]', {
                full_name: 'Alice',
                realm_name: organization_name,
                password: 'password',
                terms: true
            }, true);
        }
    });

    this.waitWhileSelector('form[action^="/accounts/register/"]', function () {
        casper.test.assertUrlMatch(realm_host + '/invite/', 'Invite more users page loaded');
    });
});

// Tests for invite more users page
casper.then(function () {
    this.waitForSelector('.app-main.portico-page-container', function () {
        this.test.assertSelectorHasText('.app-main.portico-page-container', "You're the first one here!");
    });

    this.waitForSelector('.invite_row', function () {
        this.test.assertSelectorHasText('.invite_row', domain);
    });

    this.waitForSelector('#submit_invitation', function () {
        this.click('#submit_invitation');
    });

    this.waitWhileSelector('#submit_invitation', function () {
        this.test.assertUrlMatch(realm_host, 'Realm created and logged in');
    });
});

casper.then(function () {
    // The user is logged in to the newly created realm
    this.test.assertTitle('home - ' + organization_name + ' - Zulip');
});

common.then_log_out();

casper.run(function () {
    casper.test.done();
});
