Title: How I Contribute to Open Source Projects
Date: 2021-06-27
Category: OSS, Projects
Slug: oss-how-why
Summary: A short explanation of my open source process.

Contributing to public projects is one of the most fulfilling aspects
of my software development practice. It allows me to make new
professional connections and gain exposure to challenges I would never
encounter on the job. But it *is* effortful, especially after a full
day of paid work. Over time, I've developed (mostly by trial and
error) a process that makes it easier for me to fit open source work
into my schedule and make this extra effort worthwhile.

Earlier in my career I wanted to contribute to public projects but
didn't know how to begin. In this post, I tried to provide a concise
summary of the advice I wish I'd received long ago.

## Why contribute?

Like most engineers, my paid work has been on years-long,
closed-source projects driven by deadlines and business
requirements. In that context, it's normal to build with the most
standard components possible. If your Django app needs flash messages,
you probably want to use the [messages
framework](https://docs.djangoproject.com/en/3.2/ref/contrib/messages/),
rather than rolling your own solution; there just isn't much business
value in writing something new. As a result, there are some design
problems you don't get to spend much time thinking about while doing paid
work.

Working on OSS projects lets me to grow my skills beyond boundaries
imposed by business concerns. For instance, working on [this
issue](https://github.com/aantron/dream/issues/43) let me build a
flash message system for a new web framework,
[Dream](https://aantron.github.io/dream/). Within the structure of
that project, I had an opportunity to study how Rails, Django, and
Phoenix implement flash messages. Discussing the merits of these
different approaches with more experienced engineers helped me become
a better designer.

I've also found that OSS projects are an effective way to practice the
investigative skills I use on the first few months of a new job. When
I join an organization, I have to get up to speed on new codebases
(sometimes in a language I haven't used before).  Working on an
unfamiliar open source project simulates these conditions, without the
accompanying pressures of a new job.

## How do I find new projects to work on?

Conferences focused on a specific programming language or family of
technologies are a great way to meet maintainers. When I attended
[Compose 2017](http://www.composeconference.org/2017/), a
serendipitous conversation in between sessions led to a 3-4 month
period of making contributions to
[lwt](https://github.com/ocsigen/lwt/), learning a lot more about
OCaml, and this [blog
post](https://jsthomas.github.io/map-comparison.html).

Conferences *can* be a bit of a gamble. The costs of travel, lodging,
and fees are significant. Most conferences will post their talks
later. Watching these is a great way to stay informed. This Strange
Loop [talk](https://youtu.be/gCWtkvDQ2ZI), for instance, gave me a
good overview of the Unison programming language, which eventually
allowed me to contribute this
[change](https://github.com/unisonweb/unison/pull/1639). This approach
is much more efficient for finding projects that spark your interest,
since you can watch talks at 2x speed and skip ones that aren't
useful.

## Evaluating whether a project is a good fit

Once I've found a project (usually on github) that I think is
interesting, there are a few things I check before deciding whether to
contribute.

First, I look at whether the project has recent commits. If the most
recent commit is more than a few months old, that might mean the
project is abandoned. Since I'm interested in being a contributor
rather than a maintainer, working on these repos is usually not a good
use of time.

The second thing I look at are the project's pull requests. If there
are many old, open pull requests (ones that don't have any comments),
this is another sign that the project might be abandoned. Looking
through closed PRs, or PRs with a lot of comments, typically gives me
some idea of how contributors and maintainers interact. The
maintainers I've interacted with have been friendly and welcoming; I
avoid projects where that isn't the norm.

Next, I'll take a look at the project's issue list. If users and
maintainers write clearly, it's much easier for me to make progress on
an issue without having to ask too many questions. Issues with links
to relevant code, minimal working examples, and repro steps are all
good signs.

I also look to see whether the project has Travis or Circle CI set up,
since that means I can get quick feedback on a PR without talking to
anyone. The CI systems is also helpful as a model for setting up my
development environment; often I will look through the CI
configuration in order to run my unit tests with the exact same
databases/dependencies/settings.

Finally, I'll take a more in-depth look at the codebase itself. At
this point, I'm just trying to answer basic questions, like:

- How is the source tree organized?
- Do most of the functions/classes/modules have comprehensible names?
- Where are the tests? Where would I add new tests?
- Are there comments?

## Finding a task

Once I'm confident that I want to participate, my next step is to
choose an open issue to work on. Ones that are marked "good first
issue" or "beginner" are great for a first contribution, and I'll
often start with those.

I try to keep the scope of my first contribution small. For example,
[this issue](https://github.com/arenadotio/pgx/issues/97) on the OCaml
library `pgx` asked for someone to add support for a different
date-time library (in this case `ptime`) because not everyone can use
Jane Street's `Core` library. This was an ideal first issue because I
could use the existing `Core` implementation as a model for what I
needed to build.

If an issue is a little bit old, it's a good idea to leave a note
asking whether the maintainer is still interested in having it
addressed. For example, I was interested in working on this
[issue](https://github.com/aantron/dream/issues/43), but it was a
month old. Rather than jumping into an implementation that might go to
waste, I left a comment expressing interest and offering some design
ideas. Replies in that thread allowed me to create this [pull
request](https://github.com/aantron/dream/pull/62), confident in the
knowledge that someone would want to use my work.

Once I've picked out task, it's (finally) time to implement a
solution. If I can get as far as implementing some unit tests and
getting most of them to pass, I post a comment on the issue indicating
that I'm working on a pull request. Personally, I consider it best
practice to *only* post one of these comments if I'm very confident
that I'll have a PR ready in the next few days. Conversely, no-one
wants to duplicate effort, so it's courteous to indicate that you're
preparing a PR.

## Pull request and review

Since pull requests take time to review, I try to perform at least one
round of self-review before opening a PR. Generally, I won't open a PR
unless I have fairly good test coverage for my work and the tests (and
lint steps) are passing. At a paid position, it's easy to have a
meeting or use slack to discuss a change. Public projects tend to be
more asynchronous, so it's important to read instructions carefully,
write clearly, and address obvious issues on your own.

When I write a description for my PR, I include a link to the issue it
addresses, usually in the first sentence. If the change adds new types
or functions, I include a summary of that as well. If there are design
details I'm unsure of, I flag these with comments so that the
reviewer(s) can discuss them with me.

The code review process on a public project can be a little different
from code review inside a company. At some jobs, I've observed an
unspoken rule that PRs need to be more or less correct on the first or
second try, otherwise you'll be considered ineffective. My sense is
that the review process on public projects is much more
iterative. Sometimes it isn't possible to gather all of the necessary
requirements until a first PR is drafted and people have something to
react to. It can take several rounds of revision before all of the
interested parties agree that the design is right.

This [PR](https://github.com/aantron/dream/pull/62) for instance,
required several tries to find a flash message implementation that fit
with the philosophy of the project. These situations are an
opportunity to practice discussing (and justifying) your design
decisions with other technical-minded people. I think the key to
success with public reviews is to read reviewer's comments carefully,
make an effort to understand their goals, and then fit your changes to
support those goals.

## General suggestions

If you plan on making OSS contributions long term, I'd suggest having
both a schedule and dedicated hardware for your work. Working after
dinner from 6 to 8 PM weeknights helps me get into a productive
mindset quickly. Time-boxing my work also helps me avoid exhausting my
interest in a project by putting in too many consecutive hours. Using
an inexpensive, second-hand laptop for my public projects makes it
easy for me to suspend my work when I'm done for the night and then
start the next day exactly where I left off, without having to set up
my browser/editor/terminals again.
