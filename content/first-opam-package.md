Title: What I learned publishing an open source package
Date: 2021-10-20
Category: OSS, Projects
Slug: first-opam-package

Today I published my first package on OPAM! You can find `tidy_email`
and its sub-libraries (`tidy_email_mailgun`, `tidy_email_sendgrid`,
and `tidy_email_smtp`)
[here](https://opam.ocaml.org/packages/tidy_email/tidy_email.0.0.1/). This
wrapped up a goal I wanted to accomplish while at [Recurse
Center](https://www.recurse.com/): Writing a simple (but useful) OCaml
library and making it available via `opam`.

I chose this project for several reasons:

1. I wanted more experience designing small APIs in OCaml.
2. I thought releasing a small library would help me understand how
"open source maintainer" work differs from paid closed-source
application development.
3. I wanted to learn more about the mechanics/process of packaging
   code for OPAM.

The rest of this post explains the process I used and which parts
worked well. Most of this discussion is applicable to general open
source development, but some of the tooling-related points are
specific to OCaml.

# Picking a Topic

When I started my batch at RC, I knew that I wanted to publish
_something_, but hadn't settled on a topic. Contributing to other
projects was a valuable source of ideas. After working on a couple of
issues for the web framework
[Dream](https://github.com/aantron/dream), I wrote a small [blog
post](https://jsthomas.github.io/ocaml-email.html) showing how to
build a simple email feature with Mailgun. That started a discussion
with other Dream contributors about how to simplify the implementation
of email features.

After a few more conversations, I decided to write an "adapter"
library that creates a consistent interface across different email
services. Instead of having to study Mailgun or Sendgrid's REST API
and worry about the details of making HTTP requests, you can install
`tidy_email`, provide your API keys, and use a `send` function that
consumes a simple email type. The library also makes switching email
providers as simple as changing your credentials.

I intentionally kept the scope of the library very small, since this
allowed me to complete the project in a short time frame
while learning several new skills/systems.

# Looking at "Prior Art"

Before I started implementing, I researched existing libraries that
dealt with email. This took time but paid dividends by helping me to
avoid re-inventing existing functionality. I learned more about
[`letters`](https://github.com/oxidizing/letters/), a library for
sending email via SMTP and supporting libraries like
[`mrmime`](https://github.com/mirage/mrmime) for parsing and
generating email. Later, I utilized some of these libraries while
adding an SMTP option to `tidy_email`.

Investigating other work in the OCaml web development space helped me
to articulate some of the design goals for my library.  I looked at
the web framework
[sihl](https://github.com/oxidizing/sihl/tree/master/sihl-email),
which has email among it's many capabilities, and realized I wanted to
make a very "slim" library that didn't couple sending email with other
dependencies related to SQL, HTTP, etc.

# Picking a Name

Naming things is hard! I spent some time looking through OPAM to see
which names were already taken (`emile`, `letters`). Ultimately, I
decided on these constraints:

- The name needed to be short, easy to search and remember.
- Ideally it would have only simple English words in it.
- The name should relate to email in an obvious way.

I settled on `tidy_email` based on Dream's description as a "tidy,
feature-complete web framework". The goal of the library would be to
provide a "tidy" (i.e. well-designed, beginner-friendly) API for
sending mail, and hopefully appeal to people who also like Dream.

One mistake I made early on was not sticking to a consistent naming
scheme; I had `tidy-email`, `tidy_email`, and "tidy email" in
different places. Fortunately, github makes it fairly easy to re-name
a repo if you change your mind later; it will even redirect from the
old repo name to the new one.

# Writing a First Draft

Even though `tidy_email` is quite simple. It took me some time to set
all the resources up.

Before I could get an account with Sendgrid, I had to register a
domain and create a simple website. I used AWS for this because I was
already familiar with it from past jobs. I also needed to register for
Mailgun and create keys for API and SMTP access. At some point, I had
accumulated enough credentials that I needed to set up password
management to stay organized.

Once I had access to services, I was able to write a first draft of
the library. This turned out to be harder than I expected! I wasted a
lot of time over-complicating my code with new concepts I had learned
(functors and higher order modules). Eventually I came to my senses
and wrote a much simpler implementation.

I found keeping good notes to be quite helpful in this phase. Later, I
turned these notes into documentation explaining how to set up mail
services and some relevant trade-offs when choosing a service (tl;dr:
Mailgun was the easiest, lowest-commitment way to get started).

# Getting Feedback

My main advice is: Don't go it alone. Having someone (ideally a more
experienced maintainer) review early drafts of work was really
valuable for staying on track. This helped me:

- Understand how new users would think.
- Re-order things to make them easier for first-time users to understand.
- Remove confusing or superfluous parts of my API.
- Leverage github features I wasn't aware of (actions and secrets).

I also found it helpful to attend [OCaml
Cafe](https://discuss.ocaml.org/t/ocaml-cafe-wed-oct-13-1pm-u-s-central/8610)
(this is currently meeting on Zoom). A lecture about `dune` given by
Rudi Grinberg showed me some techniques that made managing multiple
`.opam` files much easier.

# Testing

I didn't keep a careful count of my hours but I estimate that more
than half were spent writing unit and integration tests. Setting these
up early made it much easier to iterate on my design and accept pull
requests. Github actions were pretty straightforward to configure
(specified with a simple YAML
[file](https://github.com/jsthomas/tidy_email/blob/main/.github/workflows/test.yml))
after looking at a few examples. I appreciated not having to sign up
for yet another service in order to get a simple CI system working.

In `tidy_email`, an "integration test" is just a small executable that
tries to send an email to a mailbox. I used github secrets to add API
keys to my project so that integration tests could run securely on an
PR/merge that I made. It would've been nice to be able to run
integration tests on outside PRs automatically, but there isn't really
a way to do that securely.

Integration tests ended up being very advantageous for shaking out
problems that new users are likely to encounter. For example, by
testing with (intentionally) invalid SMTP credentials, I
[learned](https://jsthomas.github.io/smtp-debugging.html) that Mailgun
can terminate SMTP connections in a way that is hard for `colombe` to
handle. Debugging this example gave me some valuable experience
digging into `tidy_email`'s dependencies and helped me file a good bug
report to help improve `colombe`.

# Documentation

I spent more time than expected writing documentation. The main lesson
I learned is: _Don't bury the lede._ When people look at your repo,
they have limited time. Therefore, the first things you should show
them are

1. A simple, one sentence summary of what the library does.
2. A minimal working example (code) illustrating the library in action.

Everything that comes after this introduction should be in the service
of getting the user set up as painlessly as possible. In my case, that
meant adding sign-up links to the relevant services the library
supports. I also provided a brief explanation of the trade-offs when
choosing a service.

`tidy_email` is small enough that I didn't write documentation beyond
a readme, comments in the code, and folders of working examples. I
think for a project any larger than this, I would have had to invest
some time thinking about how to generate and host a static site with
documentation (e.g. ReadTheDocs).

# Release

Publishing my code on [opam](https://opam.ocaml.org/) was relatively
painless. To sum up the process:

0. I ran `dune build` one final time and verified my opam files were
   up to date.
1. I created a "tag" for my project (`git tag -a 0.0.1 && git push origin 0.0.1`).
2. I ran "opam publish", which created a [pull
   request](https://github.com/ocaml/opam-repository/pull/19816) on
   `ocaml/opam-repository`.
3. ~12 hours later my PR passed CI and was approved.
4. About 6 hours after that, my PR was merged and showed up on `opam`.

My [first
attempt](https://github.com/ocaml/opam-repository/pull/19634) at
publishing didn't pass CI because of some simple mistakes I made in my
`.opam` files. Fixing these was relatively straightforward after
reading the docs and looking at some other repos for reference.

# Final Thoughts

None of the work involved with releasing `tidy_email` was especially
_hard_, but there were _many_ small tasks to understand. Compared to
paid application development work, I found that this project had more
"admin work": signing up for services, configuring things, and writing
prose.

Overall, I found this type of work quite rewarding. It has been fun to
see new people discover and star the repo on Github. The project
motivated me to learn aspects of email that I would not have otherwise
explored. Given how much open source software I use, it feels great
to make a small contribution to the community.
