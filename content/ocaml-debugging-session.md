Title: Debugging an SMTP Integration in OCaml
Date: 2021-08-25
Category: OCaml, SMTP, Debugging
Slug: smtp-debugging
Summary: Things I learned while fixing some SMTP problems.

For the last few weeks I've been working on a side project to create a
small library called
[`tidy_email`](https://github.com/jsthomas/tidy-email) that makes it
easier to send email in OCaml. The repository has some example
programs illustrating how to connect to different email services. I
wanted to make sure that these programs would fail gracefully if
configured with the wrong credentials. But when I ran my example [SMTP
app](https://github.com/jsthomas/tidy-email/blob/main/smtp/example/send.ml)
with an invalid password, I saw this:

```
Send failed. Details: Error: Stack overflow
```

I expected to see some sort of "not authorized" message. Why was
this happening? This post summarizes how I debugged this problem.

## Context

Among email services (like Mailgun, Sendgrid, and Amazon SES) there
are typically two ways for a web application to send email: make a
request to a REST API or use
[SMTP](https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol). REST
APIs are convenient because they expose more features. In particular,
when you provide malformed data, the API can respond with a detailed
explanation of what the application did incorrectly. On the other
hand, SMTP is advantageous if you already have a mail server, want to
integrate with a legacy system, or can't be bothered to write a custom
REST API integration.

`tidy_email` provides a simple wrapper around other libraries that
handle HTTP requests and/or SMTP. For SMTP, it uses
[`letters`](https://github.com/oxidizing/letters), which in turn
depends on a library called
[`colombe`](https://github.com/mirage/colombe/). At a high level, what
I wanted to understand was why `letters` was experiencing a stack
overflow when provided with bad SMTP credentials.

The specific SMTP server I was testing against was provided by
Mailgun. I had previously had some
[difficulties](https://github.com/oxidizing/letters/issues/35) with
this server; these came about because Mailgun's implementation doesn't
strictly adhere to the relevant RFCs, and I thought something similar
might be occurring here.

## Gathering Data

I started by cloning the `letters` and `colombe` repositories from
github. Fortunately, I already had
[`merlin`](https://github.com/ocaml/merlin/wiki/emacs-from-scratch#configuring-your-project)
installed for Emacs. This gave me the ability to jump from a function
call in my source code to the function's definition (`C-c l`). It also
allowed me to quickly look up types (`C-c t`). These hotkeys were
invaluable for efficiently working with unfamiliar code.

Before I started digging into the source code, I tried running
`strace` on my test app. This tool produces a log of all system calls
made by the app under test. This results in a _lot_ of output; here is
an excerpt of what I saw:

```
read(5, "220 Mailgun Influx ready\r\n", 4096) = 26
read(5, 0x56132a92d460, 4096)           = -1 EAGAIN (Resource temporarily unavailable)
write(5, "EHLO glenmeretechnologies.com\r\n", 31) = 31
getpid()                                = 15565
epoll_wait(3, [{EPOLLIN, {u32=5, u64=8589934597}}], 64, 9879) = 1
read(5, "250-smtp-out-n02.prod.us-west-2."..., 4096) = 144
read(5, 0x56132a92d460, 4096)           = -1 EAGAIN (Resource temporarily unavailable)
write(5, "STARTTLS\r\n", 10)            = 10
getpid()                                = 15565
epoll_wait(3, [{EPOLLIN, {u32=5, u64=8589934597}}], 64, 9840) = 1
read(5, "220 Go ahead\r\n", 4096)       = 14
brk(0x56132a954000)                     = 0x56132a954000
brk(0x56132a975000)                     = 0x56132a975000
brk(0x56132a996000)                     = 0x56132a996000
read(5, 0x56132a92d460, 4096)           = -1 EAGAIN (Resource temporarily unavailable)
write(5, "\26\3\3\2\0\1\0\1\374\3\0033y\374\354\246\200\2749u\7\375P\226\273\37\342|\257\235\277h"..., 517) = 517
getpid()                                = 15565
epoll_wait(3, [{EPOLLIN, {u32=5, u64=8589934597}}], 64, 9796) = 1
read(5, "\26\3\3\0Z\2\0\0V\3\3\22c1v\234\367\0\322fR\230\264\236;\314\f\23\234$\245\33"..., 4096) = 3389
read(5, 0x56132a92d460, 4096)           = -1 EAGAIN (Resource temporarily unavailable)
...
read(5, "", 4096)                       = 0
(last line repeats hundreds of times)
```

From this output, I was able to glean a couple of things:

1. My app is successfully connecting to `smtp.mailgun.org`, as
   evidenced by the `220 Go ahead` message.

2. The hundreds of `read` calls seem related to the stack overflow
   issue. They suggest some sort of infinite loop or that the app is
   trying to read data that isn't available for some reason.

## Getting more information about SMTP

At this point, I decided I needed to learn a little bit about how SMTP
works. Fortunately, wikipedia provides a fairly concise
[overview](https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol)
with an example of a successful SMTP session (`S` = Server, `C` = Client):

```
S: 220 smtp.example.com ESMTP Postfix
C: HELO relay.example.com
S: 250 smtp.example.com, I am glad to meet you
C: MAIL FROM:<bob@example.com>
S: 250 Ok
C: RCPT TO:<alice@example.com>
S: 250 Ok
C: RCPT TO:<theboss@example.com>
S: 250 Ok
C: DATA
S: 354 End data with <CR><LF>.<CR><LF>
C: From: "Bob Example" <bob@example.com>
C: To: Alice Example <alice@example.com>
C: Cc: theboss@example.com
C: Date: Tue, 15 Jan 2008 16:02:43 -0500
C: Subject: Test message
C:
C: Hello Alice.
C: This is a test message with 5 header fields and 4 lines in the message body.
C: Your friend,
C: Bob
C: .
S: 250 Ok: queued as 12345
C: QUIT
S: 221 Bye
```

Unfortunately, this excerpt doesn't explain much about how a session
using STARTTLS should look. Since I saw some successful `read` calls
in my strace output, with arguments that weren't readable text, I
inferred that TLS was probably interfering with my ability to easily
see what was going on in the session after the first 220 response.


## Getting more data from logs

I used `merlin` to jump to the [relevant
parts](https://github.com/mirage/colombe/blob/master/sendmail/sendmail_with_starttls.ml)
of the `colombe` source code and noticed that `colombe` uses the
`Logs` module. Adding these two lines at the start of my test app
allowed me to start collecting log output, and see what was going on
in `colombe`:

```ocaml
  Logs.set_reporter (Logs.format_reporter ());
  Logs.set_level (Some Logs.Info);
```

When I took a look at the log output, I saw:
```
...
send: [INFO] Return
send: [INFO] READ : 220 Mailgun Influx ready
send: [INFO] READ : 250-smtp-out-n01.prod.us-west-2.postgun.com
250-AUTH PLAIN LOGIN
250-SIZE 52428800
250-8BITMIME
250-SMTPUTF8
250-PIPELINING
250 STARTTLS
...
send: [INFO] Return
send: [INFO] READ :
send: [INFO] Return
send: [WARNING] The server send an invalid base64 value: "Go ahead"
send: [INFO] READ :
send: [INFO] Return
send: [INFO] Response 535 Authentication failed
send: [INFO] Quitting connection...
send: [INFO] Before recv...
send: [INFO] READ :
(repeats, hundreds of times)
...
```

Similar to the `strace` results, I could see many failed reads. But
this time I could see they occurred after a `535 Authentication
failed` message came back from the server.

During this phase of analysis it was helpful to be able to add my own
log points to the source code. In order to do this, though, I needed
to ensure that my test app would build against my modified version of
`colombe`, not the published version on `opam`. Within the `colombe`
repo, I ran

```bash
dune build src && dune install colombe && dune build sendmail && dune install sendmail
```

This pinned both `colombe` and `sendmail` to my local versions on
disk. Because `letters` uses these two libraries, I also needed to go
to my `letters` repo and run:

```bash
dune build . && dune install letters
```

With these two steps taken care of, I could use `dune` to execute my
test app and see the custom instrumentation that I'd added to the
underlying libraries.

## Reproducing the problem

At this point, I was pretty confident that `colombe` was having
problems immediately after trying to quit the SMTP session by sending
a `QUIT`. After some google searching, I learned that `openssl`
allows you to run an SMTP session interactively. To test, I ran:

```
openssl s_client -connect smtp.mailgun.org:587 -starttls smtp
```

The first part of the session looked like this:

```text
250 STARTTLS
---
Post-Handshake New Session Ticket arrived:
SSL-Session:
    Protocol  : TLSv1.3
    Cipher    : TLS_AES_128_GCM_SHA256
    Session-ID: 7E83FE3CC7D65BE60AF56A2E049C09A27AB33DF834454617B81C0469A32EEC62
    Session-ID-ctx:
    Resumption PSK: 4A7C875CECCCA5633D3FF2107857EAF220FF561B782AAC3AC416385612E08AAB
    PSK identity: None
    PSK identity hint: None
    SRP username: None
    TLS session ticket lifetime hint: 604800 (seconds)
    TLS session ticket:
    0000 - 4a 79 8c 03 d5 1e 3f 5d-dc b2 2d b6 38 db 4e 10   Jy....?]..-.8.N.
    0010 - 91 b6 1d 44 d2 95 c9 50-f3 f9 a7 89 8d 0e b9 7e   ...D...P.......~
    0020 - f1 d6 52 da 3d 84 f5 ee-58 72 a8 81 1e 0f ad c7   ..R.=...Xr......
    0030 - c7 76 8f 8c d9 d9 56 8f-f3 72 de 0e bf 17 b0 2f   .v....V..r...../
    0040 - 72 a7 98 cd 92 46 da 45-fc b8 a9 d4 6e 73 71 f5   r....F.E....nsq.
    0050 - 74 f2 1d eb 83 b3 01 83-77 3f 7a e0 9a 36 4a fe   t.......w?z..6J.
    0060 - b3 89 3e c7 4c aa 87 eb-6d 46 42 46 73 8f 35 1f   ..>.L...mFBFs.5.
    0070 - 8c                                                .

    Start Time: 1630180065
    Timeout   : 7200 (sec)
    Verify return code: 0 (ok)
    Extended master secret: no
    Max Early Data: 0
---
read R BLOCK
EHLO
250-smtp-out-n02.prod.us-west-2.postgun.com
250-AUTH PLAIN LOGIN
250-SIZE 52428800
250-8BITMIME
250-SMTPUTF8
250 PIPELINING
```

By running `EHLO`, I was able to see the different operations this
SMTP server supports. In the output above, we can see that one of
those operations is `AUTH PLAIN`. I tried to authenticate with invalid
credentials, and saw this:

```text
AUTH PLAIN BADPASSWORD
501 Invalid response encoding
535 Authentication failed
closed
```

This means that after a client provides bad credentials, Mailgun's
SMTP implementation immediately terminates the connection. But, when
`colombe` encountered a failure to authenticate, it tried to clean up
the session like this:

```ocaml
let properly_quit_and_fail ctx err =
  let open Monad in
  let* _txts = send ctx Value.Quit () >>= fun () -> recv ctx Value.PP_221 in
  Error err
```

So `colombe` tried to send a `QUIT` message and await a `221 Bye`, but
that message never arrived because the server had already closed the
connection.


## Fixing the problem

Once I understood the problem, I realized I could avoid the issue by
revising `properly_quit_and_fail` to prevent waiting on a response
from the server. Effectively, this meant changing a `let*` to a `let`:

```ocaml
let properly_quit_and_fail ctx err =
  let open Monad in
  let _txts = send ctx Value.Quit () >>= fun () -> recv ctx Value.PP_221 in
  Error err
```

I also filed this
[issue](https://github.com/mirage/colombe/issues/46), which prompted
one of the maintainers to
[refactor](https://github.com/mirage/colombe/pull/47) how connections
are managed, with a much more thorough solution than what I had
done. (Many thanks to Calascibetta Romain for fixing my issue so
quickly!) Once merged, other `colombe` users shouldn't encounter the
stack overflow issues I described here.


## Final Thoughts

This was an interesting bug to investigate because it covered a number
of unfamiliar topics. I didn't know much about SMTP when I started,
and I learned a couple useful facts while debugging:

- SMTP sessions consist of a handful of commands that are fairly easy
  to understand.
- OpenSSL's tooling makes it easy to test SMTP by hand.
- Even very commonly used mail services like Mailgun may not work
  exactly the way you expect from reading RFCs or other documentation!

I also learned some useful techniques I can reuse the next time I need
to debug OCaml problems:

- When writing test apps, enable logging (at info level) from the
  beginning!
- Use `dune install` to add instrumentation and temporary bug fixes to
  libraries.
- Developer tooling like `merlin` is very helpful for efficiently
  navigating unfamiliar code.

## Feedback

If you found this post useful (or conversely, found an error), send me
an email. I'm interested in adding more tutorial resources to the
OCaml ecosystem and would happy to hear suggestions about how to make
these resources better. My contact information is listed on the
[About](/) page.
