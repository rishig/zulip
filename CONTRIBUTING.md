# Contributing to Zulip

Thank you for being here!

## Community

<https://chat.zulip.org> is the primary communication forum for the Zulip
community. It is a good place to start whether you have a question, are a
new contributor, are a new user, or anything else.

You can read more about the community
[here](http://zulip.readthedocs.io/en/latest/chat-zulip-org.html). A few
norms to know right away are to send test messages to
[#test here](https://chat.zulip.org/#narrow/stream/test.20here), and to use
gender-neutral language. The community is also governed by a
[Code of Conduct](http://zulip.readthedocs.io/en/latest/code-of-conduct.html).

You can subscribe to zulip-devel@googlegroups.com for a lower traffic (~1
email/month) way to hear about things like mentorship opportunities with Google
Code-in, in-person sprints at conferences, and other opportunities to
contribute.

## Ways to contribute

To make a code or documentation contribution, read
[our step-by-step guide](#your-first-codebase-contribution) to getting
started with the Zulip codebase. A small sample of the type of work that
needs doing:
* Bug squashing and feature development on our
  [Python/Django backend, web frontend](https://github.com/zulip/zulip),
  [React Native mobile app](https://github.com/zulip/zulip-mobile), or
  [Electron desktop app](https://github.com/zulip/zulip-electron).
* Building our [bots framework](https://github.com/zulip/python-zulip-api).
* [Writing an integration](http://zulip.readthedocs.io/en/latest/integration-guide.html).
* Improving our [user](https://chat.zulip.org/help/) or
  [developer](zulip.readthedocs.io/en/latest/) documentation.
* [Reviewing code](http://zulip.readthedocs.io/en/latest/code-reviewing.html)
  and manually testing pull requests.

**Non-code contributions**: Some of the most valuable ways to contribute don't require touching the
codebase at all. We list a few of them below:

* [Reporting issues](#reporting-issues), including both feature requests and
  bug reports.
* [Giving feedback](#user-feedback) if you are evaluating or using Zulip.
* [Translating](https://zulip.readthedocs.io/en/latest/translating.html)
  Zulip.
* [Outreach](#outreach): Star us on GitHub, upvote us
  on product comparison sites, or write for the Zulip blog.

## Your first (codebase) contribution

This section has a step by step guide to starting as a Zulip codebase
contributor. It looks long, but don't worry about doing all the steps
perfectly; no one gets it right the first time, and there are a lot of
people available to help.
* First, read about our
  [community conventions](http://zulip.readthedocs.io/en/latest/chat-zulip-org.html),
  and make an account at <https://chat.zulip.org>. If you'd like, introduce
  yourself in
  [#new members](https://chat.zulip.org/#narrow/stream/new.20members), using
  your name as the topic. Bonus: tell us about your first impressions of
  Zulip, and anything that felt confusing/broken as you started using the
  product.
* Read [What makes a great Zulip contributor](#what-makes-a-great-zulip-contributor).
* [Install the development environment](zulip.readthedocs.io/en/latest/dev-overview.html),
  getting help in
  [#development help](https://chat.zulip.org/#narrow/stream/development.20help)
  if you run into any troubles.
* Read the
  [Zulip guide to Git](http://zulip.readthedocs.io/en/latest/git-guide.html)
  and do the Git tutorial (coming soon) if you are unfamiliar with Git,
  getting help in
  [#git help](https://chat.zulip.org/#narrow/stream/git.20help) if you run
  into any troubles.
* Sign the
  [Dropbox Contributor License Agreement](https://opensource.dropbox.com/cla/).

**Picking an issue**

Now you're ready to pick your first issue. There are hundreds of open issues
in the main codebase alone. This section will help you find an issue to work
on.

* If you're interested in
  [mobile](https://github.com/zulip/zulip-mobile/issues?q=is%3Aopen+is%3Aissue),
  [desktop](https://github.com/zulip/zulip-electron/issues?q=is%3Aopen+is%3Aissue),
  or
  [bots](https://github.com/zulip/python-zulip-api/issues?q=is%3Aopen+is%3Aissue)
  development, check the respective links for open issues, or post in
  [#mobile](https://chat.zulip.org/#narrow/stream/mobile),
  [#electron](https://chat.zulip.org/#narrow/stream/electron), or
  [#bots](https://chat.zulip.org/#narrow/stream/bots).
* For the main server and web repository, start by looking through issues
  with the label
  [good first issue](https://github.com/zulip/zulip/issues?q=is%3Aopen+is%3Aissue+label%3A"good+first+issue").
  These are smaller projects particularly suitable for a first contribution.
* We also partition all of our issues in the main repo into areas like
  admin, compose, emoji, hotkeys, i18n, onboarding, search, etc. Look
  through our [list of labels](https://github.com/zulip/zulip/labels), and
  click on some of the `area:` labels to see all the issues related to your
  areas of interest.
* If the lists of issues are overwhelming, post in
  [#new members](https://chat.zulip.org/#narrow/stream/new.20members) with a
  bit about your background and interests, and we'll help you out. The most
  important thing to say is whether you're looking for a backend (Python),
  frontend (JavaScript), mobile (React Native), desktop (Electron),
  documentation (English) or visual design (JavaScript + CSS) issue, and a
  bit about your programming experience.

We also welcome suggestions of features that you feel would be valuable or
changes that you feel would make Zulip a better open source project, and are
happy to support you in adding new features or other user experience
improvements to Zulip. If you have a new feature you'd like to add, we
recommend you start by posting in
[#new members](https://chat.zulip.org/#narrow/stream/new.20members) with the
feature idea and the problem that you're hoping to solve.

Other notes:
* For a first pull request, it's better to aim for a smaller contribution
  than a bigger one.
* The full list of issues in need of contribution can be found with the
  [help wanted](https://github.com/zulip/zulip/issues?q=is%3Aopen+is%3Aissue+label%3A%22help+wanted%22)
  label.

**Working on an issue**

To work on an issue, claim it by adding a comment with `@zulipbot claim` to
the issue thread. This will assign you to the issue and label the issue as
*in progress*. Some additional notes:

* You're encouraged to ask questions on how to best implement or debug your
  changes -- the Zulip maintainers are excited to answer questions to help
  you stay unblocked and working efficiently. You can ask questions on
  chat.zulip.org, or on the GitHub issue or pull request.

* We encourage early pull requests for work in progress. Prefix the title of
  work in progress pull requests with `[WIP]`, and remove the prefix when it
  is ready for final review.

## What makes a great Zulip contributor?

Zulip runs a lot of internship programs, so we have a lot of experience with
new contributors. In our experience, these are the best predictors of success:

* Posting good questions. This generally means explaining your current
  understanding, saying what you've done or tried so far, and including
  tracebacks or other error messages if appropriate.
* Learning and practicing
  [Git commit discipline](http://zulip.readthedocs.io/en/latest/version-control.html#commit-discipline).
* Submitting carefully tested code.
* Being helpful and friendly on <https://chat.zulip.org>.

These are also the main criteria we use to select interns for all of our
internship programs.

## Reporting issues

Our preferred venue for hearing issues reports is
[#issues](https://chat.zulip.org/#narrow/stream/issues) (or
[#mobile](https://chat.zulip.org/#narrow/stream/mobile) or
[#electron](https://chat.zulip.org/#narrow/stream/electron)) on
<https://chat.zulip.org>. This allows us to interactively figure out what is
going on, let you know if a similar issue has already been opened, and
collect any other information we need. Choose a 2-4 word topic that
describes the issue, explain the issue and how to reproduce it if known,
your browser/OS if relevant, and a
[screenshot or screenGIF](http://zulip.readthedocs.io/en/latest/screenshot-and-gif-software.html)
if appropriate.

You can also open an issue on GitHub, if you prefer.

**Reporting security issues**. Please do not report security issues
  publicly, including on public streams on chat.zulip.org. You can email
  zulip-security@googlegroups.com. We create a CVE for every security issue.

## User feedback

Nearly every feature we develop starts with a user request. If you are part
of a group that is either using or considering using Zulip, it would be very
helpful to hear about your experience with the product. If you're not sure
what to write, here are some questions we're always very curious to know the
answer to:

* Evaluation: What is the process by which your organization chose or will
  choose a group chat product?
* Pros and cons: What are the pros and cons of Zulip for your organization,
  and the pros and cons of other products you are evaluating?
* Features: What are the features that are most important for your
  organization? In the best case scenario, what would your chat solution do
  for you?
* Onboarding: If you remember it, what was your impression during your first
  few minutes of using Zulip? What did you notice, and how did you feel? Was
  there anything that stood out to you as confusing, or broken, or great?
* Organization: What does your organization do? How big is the organization?
  A link to your organization's website?

## Outreach

Upvotes and reviews make a big difference in the public perception of big
projects like Zulip. We've collected a few sites below where we know Zulip
has been discussed. Doing everything in the following list typically takes
about 15 minutes.
* Star us on GitHub. There are four main repositories:
  [server/web](https://github.com/zulip/zulip),
  [mobile](https://github.com/zulip/zulip-mobile),
  [desktop](https://github.com/zulip/zulip-electron), and
  [API](https://github.com/zulip/python-zulip-api).
* [Follow us](https://twitter.com/zulip) on Twitter.

For both of the following, you'll need to make an account if you don't
already have one.

* [Like Zulip](https://alternativeto.net/software/zulip-chat-server/) on
  AlternativeTo. We recommend upvoting a couple of other products you like
  as well, both to give back to their community, and since single-upvote
  accounts are generally given less weight. You can also
  [upvote Zulip]((https://alternativeto.net/software/slack/)) on the page
  for Slack..
* [Add Zulip to your stack]() on StackShare, and upvote the reasons why
  people like Zulip that you find most compelling. Again, we recommend
  adding a few other products that you like as well.

We have a doc with more detailed instructions and a few other sites, if you
have been using Zulip for a while and want to contribute more.

**Blog posts**. Writing a blog post about your experiences with Zulip, or
about a technical aspect of Zulip can be a great way to spread the word
about Zulip.

We also occasionally publish longer form articles related to Zulip. Our
posts typically get tens of thousands of views, and we always have good
ideas for blog posts that we can outline but don't have time to write. If
you are an experienced writer or copyeditor, send us a portfolio, and we'd
love to talk!
