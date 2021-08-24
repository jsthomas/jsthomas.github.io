Title: How to send emails from Dream
Date: 2021-07-23
Category: OCaml
Slug: ocaml-email
Summary: How to build an email queue system for a Dream web server.

I recently [learned](https://github.com/aantron/dream/issues/138) the
OCaml ecosystem has most of the libraries needed to build email
features, but I wasn't able to find an example that brings all of
those pieces together. I wanted a simple example I could easily adapt
to build common account verification and password recovery workflows
in the Dream web framework. This post is my attempt to solve that
problem and explain what I learned in the process. The accompanying
code can be found
[here](https://github.com/jsthomas/dream-email-example).

## Defining the problem

As an application developer, my main concerns when
sending mail are:

1. Trying to ensure the address I'm sending to is valid.
2. Handling the email synthesis process asynchronously, so it doesn't
   block the web server from handling requests quickly.
3. Transmitting the email content (SMTP or a REST API call)
4. Monitoring that the applications messages aren't getting
   blocked/dropped for some reason.

To test how easily I could satisfy these requirements, I built a web
app that lets the user send an arbitary email.

![A screenshot of the email form.]({static}/images/ocaml-email/screenshot.png)

The app has two parts:

- A server process responsible for showing the form above and
  validating user inputs.
- A "worker" process responsible for sending mail. The worker gets its
  tasks from a queue populated by the server.


## Validating Email Addresses

I decided to utilize the library
[`emile`](https://github.com/dinosaure/emile) for address
validation. An email address might be invalid for reasons outside of
the application's control (like the domain going way), but `emile` at
least provides a way to check a given string conforms to 5(!) RFCs
relevant to parsing email addresses. Check out the
[tests](https://github.com/dinosaure/emile/blob/master/test/test.ml#L34)
to see the impressive diversity of valid email addresses on the web.

The library provides several different predicates for checking
addresses. I utilized `Emile.of_string`, which generates a simple
result type, like this:

```ocaml
let form_post request =
  match%lwt Dream.form request with
    | `Ok ["address", address; "message", message; "subject", subject ] ->
      let parse = Emile.of_string address in
      let alert = match parse with
        | Ok _ -> Printf.sprintf "Sent an email to %s." address
        | Error _ -> Printf.sprintf "%s is not a valid email address." address
      in
      let queue_req = match parse with
        | Ok _ -> queue_email address subject message
        | Error _ -> Lwt.return_unit
    in
    queue_req >>= (fun _ ->
        Dream.html (Template.show_form ~alert request))
    | _ -> Dream.empty `Bad_Request
```

This way, if a user provides an invalid address, the form displays a simple
warning message and won't queue any email tasks.

## Queuing Tasks with RabbitMQ

The second issue I needed to address is handling the email send
process with a background worker (`queue_email` in the code excerpt
above). Sending an email can be a slow process, especially if you need
to make additional database queries or render images to produce a
customized email. That shouldn't block the web server from quickly
responding to the user's requests. Instead, the server should record
the email task in a _queue_, to be handled by a background worker that
isn't as sensitive to latency.

There are several different technologies that can be used to solve
this problem, for example [RabbitMQ](https://www.rabbitmq.com/),
[Redis](https://redislabs.com/ebook/part-2-core-concepts/chapter-6-application-components-in-redis/6-4-task-queues/6-4-1-first-in-first-out-queues/)
and [SQS](https://aws.amazon.com/sqs/). I decided to use RabbitMQ
because I didn't want to tie my implementation to one cloud provider
and RabbitMQ is supported by
[amqp-client](https://github.com/andersfugmann/amqp-client) on
OPAM. This isn't the only way to go: for Redis and SQS, you might have
success with the packages
[redis](https://opam.ocaml.org/packages/redis/) or
[aws-sqs](https://opam.ocaml.org/packages/aws-sqs/), respectively.

The worker and server process share a common function for establishing
a connection to RabbitMQ:

```ocaml
let rabbit_connection () =
  let%lwt connection = Connection.connect ~id:"dream" "localhost" in
  let%lwt channel = Connection.open_channel ~id:"email" Channel.no_confirm connection in
  let%lwt queue = Queue.declare channel ~arguments:[Rpc.Server.queue_argument] "email" in
  Lwt.return (channel, queue)
```

I was initially little confused about why I needed a "channel" when I
already had a connection to the broker. Both the worker and the server
connect to the RabbitMQ Broker via TCP. It's common for clients to
need several connections to the broker, but it's costly to have many
TCP connections. RabbitMQ lets us avoid this cost with channels, which
are like "lightweight connections that share a single TCP
connection", according to these [docs](https://www.rabbitmq.com/channels.html).

I created this function to submit messages to the queue:

```ocaml
type email = {
  address: string;
  subject: string;
  text: string;
} [@@deriving yojson]

let queue_email address subject text =
  let email = {address; subject; text} in
  let text = email |> yojson_of_email |> Yojson.Safe.to_string in
  let%lwt channel, queue = rabbit_connection () in
  let%lwt _ = Queue.publish channel queue (Message.make text) in
  Lwt.return_unit
```

Here the server writes the address, subject, and text into a record
type that can be serialized to JSON before being pushed into the queue.

The worker process, `queue_worker`, is fairly simple to define:
```ocaml
let handle_message (m: Message.t) =
  let text = snd m.message in
  let email =
    try
      Some (text |> Yojson.Safe.from_string |> email_of_yojson)
    with _ ->
      Printf.printf "Received invalid email record from RabbitMQ: %s" text;
      None
  in
  match email with
  | Some e -> send_email e
  | None -> Lwt.return_unit


let queue_worker () =
  Printf.printf "Starting Queue Worker\n";
  let%lwt channel, queue = rabbit_connection () in
  let rec handle () =
    Queue.get ~no_ack:true channel queue >>= fun message ->
    let task = match message with
      | Some m -> flush stdout; handle_message m
      | _ -> Printf.printf "No new tasks, waiting.\n"; flush stdout; Lwt_unix.sleep 5.
    in
    task >>= handle
  in
  handle ()
```

The worker consists of an infinite loop. When the worker wakes and
finds tasks in the queue, it uses `yojson` to deserialize the
messages and passes them to `send_email`. If no work is available,
the worker just sleeps for 5 seconds.

## Sending Email with `cohttp` and Mailgun

In order to send mail, I set up a trial
[Mailgun](https://documentation.mailgun.com/en/latest/quickstart-sending.html#send-via-smtp)
account. I selected this provider for several reasons:

- Mailgun has a generous free tier (5000 emails).
- A new account also comes with a "sandbox" domain, so I didn't have
  to deal with registering a domain.
- Mailgun supports both a REST API and SMTP, allowing me to try
  different integrations.
- Mailgun provides dashboards for tracking messages sent over time as
  well as emails that were rejected (bounced, marked as spam, etc.).

Mailgun's API allowed me to send an email by sending a POST with an API key and form
data, like this:
```ocaml
let send_email (e: email) =
   let open Cohttp in
   let open Cohttp_lwt_unix in

   let api_key = Sys.getenv "MAILGUN_API_KEY" in
   let sender = Sys.getenv "MAILGUN_SEND_ADDRESS" in
   let api_base = Sys.getenv "MAILGUN_API_BASE" in

   let params = [
     ("from", [sender]);
     ("to", [e.address]);
     ("subject", [e.subject]);
     ("text", [e.text])
   ] in
   let cred = `Basic ("api", api_key) in
   let uri = api_base ^ "/messages" |> Uri.of_string in
   let headers = Header.add_authorization (Header.init ()) cred in
   let start =
     Printf.printf "Initiating email send to %s.\n" e.address;
     Unix.gettimeofday () in
   let%lwt resp, rbody = Client.post_form uri ~params ~headers in
   let%lwt finish = Unix.gettimeofday () |> Lwt.return in
   let%lwt rbody_str = (Cohttp_lwt.Body.to_string rbody) in
   Printf.printf "API Response Status: %d.\n" (Code.code_of_status resp.status);
   Printf.printf "API Response body %s.\n" rbody_str;
   Printf.printf "Time to send an email: %.2fs\n" (finish -. start);
   Lwt.return ()
```

The endpoint replies with either 200 and a JSON body like this:

```json
{
  "id": "<some mailgun email address here>"
  "message": "Queued. Thank you."
}
```

or else a 400 and an explanation of why the request was rejected. In
my tests, a successful API request typically took between 0.5 and 1
seconds. For comparison, the webserver can serve the email form in
less than 200 microseconds, so the performance benefits to shifting
email tasks to a background queue are nontrivial.


## Sending email with SMTP

Mailgun supports SMTP but they recommend using their API, especially
for sending large amounts of mail at once. I used
[letters](https://github.com/oxidizing/letters/) to test their SMTP
support with this script:

```ocaml
let body = Letters.Plain {|This is a test email body.|}

let send_email () =
  let config = (Letters.Config.make
      ~username: Sys.getenv "MAILGUN_SMTP_USER"
      ~password: Sys.getenv "MAILGUN_SMTP_PASSWORD"
      ~hostname:"smtp.mailgun.org"
      ~with_starttls:true)
  in
  let sender = Sys.getenv "MAILGUN_SMTP_SENDER" in
  let recipients = [Letters.To (Sys.getenv "EMAIL_ADDRESS")] in
  let subject = "Test email from mailgun." in
  let mail = Letters.build_email ~from:sender ~recipients ~subject ~body in

  Printexc.record_backtrace true;
  match mail with
  | Ok message ->
    (try%lwt
       Letters.send ~config ~sender ~recipients ~message
    with
      e ->
      Printf.printf "Error. %s\n" (Printexc.to_string e);
      Printexc.print_backtrace stdout;
      Lwt.return_unit
   )
  | Error _ -> Printf.printf "Message synthesis failed."; flush stdout; Lwt.return_unit


let () =
  Lwt_main.run @@ send_email ()
```

I ran into some
[difficulties](https://github.com/oxidizing/letters/issues/35) because
Mailgun does not consistently follow RFC 4954 (thanks to Calascibetta
Romain for figuring out the problem and creating a
[patch](https://github.com/mirage/colombe/pull/41)). Once I applied
the patch, I was able to send mail successfully.

I haven't fully explored the tradeoffs of using SMTP versus an
API. The main goal of my experiements was to confirm that if I needed
to integrate with a specific SMTP server, I knew how to do so.

## Discussion

This example focused on email, but task queues and background workers
can be used to implement other important pieces of functionality for
web applications. For example, I've utilized
[celery](https://docs.celeryproject.org/en/stable/getting-started/introduction.html)
in the past to generate weekly reports and schedule recurring ETL
jobs. This exercise was a nice opportunity to see how one would
construct a system similar to `celery` in OCaml. It also provides a
simple illustration of how we can utilize queues to facilitate
horizontal scaling. If the volume of email requests grows too big for
one machine, we can put the web server and the worker on separate
instances or have multiple worker instances consuming from the email
queue.

I didn't cover error handling in this example, but that's clearly an
important piece of functionality to include when building a production
email system. At a minimum, it would be useful to add a retry
mechanism in the event that Mailgun is unavailable.

## References

I found the resources below helpful for working on this project:

- The `amqp-client`
  [documentation](https://andersfugmann.github.io/amqp-client/amqp-client-lwt/index.html),
  especially the
  [examples](https://github.com/andersfugmann/amqp-client/tree/master/examples)
  were helpful for setting up with RabbitMQ.
- The [client
  tutorial](https://github.com/mirage/ocaml-cohttp#client-tutorial)
  was helpful for getting started with `cohttp`. Later, I utilized
  [this
  section](https://mirage.github.io/ocaml-cohttp/cohttp-lwt-unix/Cohttp_lwt_unix/Client/index.html)
  of the docs to understand that I needed to use `post_form` instead
  of `post` when interacting with Mailgun's API.

## Feedback

If you ended up looking through the source code for this example, let
me know how what you thought! I'm interested in adding more tutorial
resources to the OCaml ecosystem, so feel free to post a PR or issue
to
[dream-email-example](https://github.com/jsthomas/dream-email-example)
if you have ideas about how to make these resources better.
