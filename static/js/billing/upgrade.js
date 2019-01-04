var upgrade = (function () {
var exports = {};

exports.initialize = () => {
    var hash = window.location.hash;
    if (hash) {
        $('#upgrade-tabs.nav a[href="' + hash + '"]').tab('show');
        $('html,body').scrollTop(0);
    }

    $('#upgrade-tabs.nav-tabs a').click(function () {
        $(this).tab('show');
        window.location.hash = this.hash;
        $('html,body').scrollTop(0);
    });

    var add_card_handler = StripeCheckout.configure({ // eslint-disable-line no-undef
        key: $("#autopay-form").data("key"),
        image: '/static/images/logo/zulip-icon-128x128.png',
        locale: 'auto',
        token: function (stripe_token) {
            helpers.create_ajax_request("/json/billing/upgrade", "autopay", stripe_token = stripe_token);
        },
    });

    $('#add-card-button').on('click', function (e) {
        var license_management = $('input[type=radio][name=license_management]:checked').val();
        if ($("#" + license_management + "_license_count")[0].checkValidity() === false) {
            return;
        }
        add_card_handler.open({
            name: 'Zulip',
            zipCode: true,
            billingAddress: true,
            panelLabel: "Make payment",
            email: $("#autopay-form").data("email"),
            label: "Add card",
            allowRememberMe: false,
            description: "Zulip Cloud Standard",
        });
        e.preventDefault();
    });

    $("#invoice-button").on("click", function (e) {
        if ($("#invoiced_licenses")[0].checkValidity() === false) {
            return;
        }
        e.preventDefault();
        helpers.create_ajax_request("/json/billing/upgrade", "invoice");
    });

    var prices = {};
    prices.annual = page_params.annual_price * (1 - page_params.percent_off / 100);
    prices.monthly = page_params.monthly_price * (1 - page_params.percent_off / 100);

    $('input[type=radio][name=license_management]').change(function () {
        helpers.show_license_section($(this).val());
    });

    $('input[type=radio][name=schedule]').change(function () {
        helpers.update_charged_amount(prices, $(this).val());
    });

    $("#autopay_annual_price").text(helpers.format_money(prices.annual));
    $("#autopay_annual_price_per_month").text(helpers.format_money(prices.annual / 12));
    $("#autopay_monthly_price").text(helpers.format_money(prices.monthly));
    $("#invoice_annual_price").text(helpers.format_money(prices.annual));
    $("#invoice_annual_price_per_month").text(helpers.format_money(prices.annual / 12));

    helpers.show_license_section($('input[type=radio][name=license_management]:checked').val());
    helpers.update_charged_amount(prices, $('input[type=radio][name=schedule]:checked').val());
};

return exports;
}());

if (typeof module !== 'undefined') {
    module.exports = upgrade;
}

window.upgrade = upgrade;

$(function () {
    upgrade.initialize();
});
