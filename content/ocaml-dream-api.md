Title: Writing a REST API with Dream
Date: 2021-07-12
Category: OCaml
Slug: ocaml-dream-api
Summary: Writing a REST API in Dream


In the last few weeks I've been building a simple REST API using the
[Dream](https://aantron.github.io/dream/) web framework. Writing APIs
has been one major component of my paid programming work and I wanted
to compare and contrast the experience of writing an API in a strongly
typed functional programming language with the same workflow in a
dynamically typed language like Python.

You can find the source code for this project
[here](https://github.com/jsthomas/sensors). Hopefully, this repo will
be a useful resource for anyone who wants to look at a slightly larger
example application that uses Dream. Though I'm still a beginner, I
was surprised how easy it was to complete familiar tasks in this
framework. I'm optimistic about the future of web programming in
OCaml!

This post provides a sort of "experience report" for working with
Dream, Yojson, and Caqti. Obviously, these types of reports are highly
subjective and you should run your own experiments too!  I'll be
comparing with my experience in working with
[Pyramid](https://trypyramid.com/) and
[SQLAlchemy](https://www.sqlalchemy.org/), since those are the Python
projects I've used most.

Finally, it's important to point out that Dream is in alpha (version
`1.0.0~alpha2` as of this writing). This is an early version!
Comparisons with frameworks like Pyramid or Flask are in some sense
apples-and-oranges, because those projects have had a long time (and
many engineering hours) to mature. Ultimately, the point of this post
(and the repo that goes with it) isn't to make make value judgements
("framework X is good, Y is bad"), but rather to understand how to
translate concepts from one workflow to another.

## Problem Definition

I decided to build a API for managing time series data. My
requirements for the project were as follows:

- The API will allow creating, reading, and deleting "sensors". A
  sensor is an abstract IoT device that measures a floating point
  quantity at a specific cadence (for example a weather station
  measuring average hourly windspeed).
- Every sensor gets an API key that allows it to upload (POST) data to
  an endpoint.
- A GET endpoint will allow users to retrieve the data a sensor
  generated between two dates.
- The API sends and receives data formatted as JSON and must be backed
  by a PostgreSQL database.
- The API should have `login/logout` endpoints for a (not yet built)
  frontend to use.
- Finally, a user should only be allowed to access sensor data that
  belongs to them.

I chose these requirements because they cover a number of different
read/write operations that require data formatting/parsing and
tracking relationships between four different entities (users, keys,
sensors, and readings).

## Dependencies and Setup

For this build, I needed three core dependencies:

1. A server to handle web requests (Dream).
2. Support for parsing and synthesizing JSON records.
3. A library for integrating with PostgreSQL.

After a bit of research, I settled on
[Yojson](https://opam.ocaml.org/packages/yojson/) and
[Caqti](https://opam.ocaml.org/packages/caqti/) for (2) and (3)
respectively. Both of these are fairly standard and appear in the
excellent corpus of
[examples](https://github.com/aantron/dream/tree/master/example) that
accompany Dream. Since I had previously written an
[example](https://github.com/aantron/dream/tree/master/example/w-docker-postgres)
of how to use Dream with a dockerized PostrgreSQL container, I used
that as a starting point.

It's useful to have a way to run (and re-run) ad-hoc requests against
the API during development. I used [Insomnia](https://insomnia.rest/)
for this, but other tools like `curl` would work too.

## Adding an endpoint

To give a sense of my development workflow, I want to walk through my
process for adding a simple endpoint, `/api/login`. Inside the router,
that endpoint looks like:

```ocaml
Dream.post "/api/login" login;
```

In this excerpt `login` is a "handler". Handlers are responsible for
translating requests into responses; this is captured in their [type
signature](https://aantron.github.io/dream/#type-handler).

Conceptually, the `login` handler needs to do three things:

1. Receive a JSON body and confirm it's formatted as expected.
2. Look up the relevant user/password combination in the database.
3. Load the relevant session information if the credentials are valid.

For the first part, the endpoint needs to receive a JSON payload that
looks like `{"username": "...", "password": "..."}`. To describe that
payload, I introduced a simple record type:

```ocaml
type login_doc = {
  username : string;
  password : string;
} [@@deriving yojson]
```

Adding `[@@deriving yojson]` means the compiler can generate functions
to convert these records to and from JSON. In this case those
functions are called `login_doc_of_yojson` and `yojson_of_login_doc`.

My `login` handler looked roughly like this:
```ocaml
let json_receiver json_parser handler request =
  let%lwt body = Dream.body request in
  let parse =
    try
      Some (body
      |> Yojson.Safe.from_string
      |> json_parser)
    with _ ->
      None
  in
  match parse with
  | Some doc -> handler doc request
  | None ->
    { error="Received invalid JSON input." }
    |> yojson_of_error_doc
    |> json_response ~status: `Bad_Request


let login =
  let login_base login_doc request =
    let%lwt user_id = Dream.sql request
        (Models.User.get login_doc.username login_doc.password) in
    match user_id with
    | Some id ->
      let%lwt () = Dream.invalidate_session request in
      let%lwt () = Dream.put_session "user" (Int.to_string id) request in
      Dream.empty `OK
    | None -> Dream.empty `Forbidden
  in
  json_receiver login_doc_of_yojson login_base
```

If a user uploads an invalid JSON body, this will cause
`login_doc_of_yojson` to throw an exception. By default, this produces
a 500 server error response. To handle this situation more gracefully,
I introduced `json_receiver`. If the parser passed to `json_receiver`
succeeds on the request body, the results are passed to the inner
handler. Otherwise, the server responds with a `400 Bad
Request`. Re-using `json_receiver` across my endpoints allows me to
avoid introducing a`try/with` block any time time I need to handle
JSON input.

I decided to manage models in a separate library, `Models`. The
build tool, `dune`, made this easy to do; I just needed separate
`dune` files for the `server/model` and `server/bin` folders. I like
this design because it simplifies re-use of the database portion of my
project. For example, if I later needed to build a CLI admin tool,
that tool could utilize my existing queries without being exposed to
API concerns.

Inside `User`, the `get` query function is defined as:
```ocaml
let get =
  let query =
    R.find_opt T.(tup2 T.string T.string) T.int
      "SELECT id FROM app_user WHERE username = ? and password = ?" in
  fun username password (module Db : DB) ->
    let%lwt user_or_error = Db.find_opt query (username, password) in
    Caqti_lwt.or_fail user_or_error
```

Caqti allows us to define a function that consumes our query
parameters (the username and password) along with a database
connection, and produces a promise that will resolve with the results
of the query. In this case, the types encode that the function
produces an `int option` containing the user's primary key if the
credentials are valid. (Note that it's not a good idea to store
passwords in plain text like this; this is just for illustrative
purposes.)

Session management, the final item that the endpoint needs to address,
is handled by Dream. The framework allows sessions to be stored in
cookies, memory, or the database; I opted for database sessions
because I had used similar session backends in the past. Sessions
allow us to store pairs key/value strings across requests. I used the
session just to store the logged-in user's ID, so that the API has
easy access in later database queries.

## Thoughts on the Dream Router

The final router for my server looked like this:

```ocaml
let () =
  Dream.run ~interface:"0.0.0.0"
  @@ Dream.logger
  @@ Dream.sql_pool "postgresql://sensors@127.0.0.1/sensors"
  @@ Dream.sql_sessions
  @@ Dream.router [
	(* More endpoints here ... *)

    Dream.get "/version" version;
    Dream.post "/api/login" login;
    Dream.post "/api/logout" logout;

    Dream.scope "/api" [login_required] [
      Dream.get "/user/:user_id" user;
	  (* More endpoints here... *)
    ];

    Dream.scope "/sensor" [] [
      Dream.post "/upload" @@ api_key_required sensor_upload;
    ]
  ]
  @@ Dream.not_found
```

I really appreciate how Dream makes it possible to get a concise
overview of the API; in some Pyramid projects, I found this wasn't
always possible. In fact, in Pyramid I sometimes struggled with subtle
routing bugs that were not obvious until run time. Having the compiler
validate the router in Dream was a welcome change.

At the moment, Pyramid makes it somewhat easier to handle
access/permissions concerns compared to Dream. Working in Pyramid, it
was relatively common for the routes to manage some amount of
parameter validation and permissions. For example, given a path
`/user/123/article/abc456`, the route (or "resources" in Pyramid
terminology) would be responsible for:

- Extracting the user and article IDs (`123` and `abc456`).
- Determining those records actually exist in the database, and
  passing them to the view/handler in a context record.
- Validating that the requester has permissions to operate on those
User and Article records.

This is discussed a bit more in the Pyramid Docs under [URL
traversal](https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/traversal.html).
Effectively, Pyramid resources mean that handler/view code downstream
can focus on updating database records and/or rendering HTML/JSON
without worrying about permissions concerns.

I didn't want to build a permissions system for my API so instead I
incorporated User IDs into my function signatures in `Model` and used
inner joins to model permissions. For example, here is an example of a
query that fetches the metadata for all sensors belonging to a
particular user:

```sql
SELECT s.name, s.description, k.uuid
FROM sensor s
INNER JOIN user_sensor us
 ON us.sensor = s.id AND us.app_user = $1 AND us.sensor = $2
INNER JOIN api_key k
 ON s.api_key = k.id
```

By joining against `user_sensor`, I ensure that a user only gets data
for the sensors they own.

I should point out that Dream allows us to use a custom router,
however! The project has [an
issue](https://github.com/aantron/dream/issues/122) for more elaborate
routing and Ulrik Strid has introduced
[dream-routes](https://github.com/ulrikstrid/dream-routes), which
allows additional type information to be encoded in routes. So,
writing a more sophisticated router that behaves like Pyramid's
resource system is certainly possible.

## Comparing Caqti and SQLAlchemy

As a web programmer, especially one working on an analytics project,
it's important to get comfortable working with the database library
you've chosen for your project. Indeed, a significant portion of this
project consisted of familiarizing myself with `Caqti`.

Caqti is a bit different from SQLAlchemy. With SQLAlchemy, you
typically define one class for each table. Then, using SQLAlchemy's
metaprogramming features, those classes are used to define
queries. For comparison, here are equivalent queries against the user
table:

**Caqti**
```ocaml
let get =
  let query =
    R.find_opt T.(tup2 T.string T.string) T.int
      "SELECT id FROM app_user WHERE username = ? and password = ?" in
  fun username password (module Db : DB) ->
    let%lwt user_or_error = Db.find_opt query (username, password) in
    Caqti_lwt.or_fail user_or_error
```
**SQLAlchemy**
```python
db.session.query(User) \
	.filter(
		User.username == username,
		User.password == password
	).one_or_none()
```

Working with Caqti, a mistake in the syntax of a SQL query won't be
discovered until runtime. I made fewer mistakes like this with
SQLAlchemy because most queries are written in Python and can be
linted by the IDE. Another recurring point of confusion for me with
Caqti had to do with matching the function on the `Caqti_request`
(`R.find_opt` above) with the function invoked in `Db`
(`Db.find_opt`); this is how we indicate that the query produces zero,
one, zero/one, or multiple rows. If the two don't agree, the program
won't compile; initially I struggled to understand what this
compiler error meant:

```
Error: The function applied to this argument has type
         ?env:(Caqti_driver_info.t -> string -> Caqti_query.t) ->
         ?oneshot:bool ->
         ('a, unit, [< `Many | `One | `Zero > `Zero ]) Caqti_request.t
This argument cannot be applied without label
```

Using Caqti became easier as I became accustomed to thinking in terms of
prepared queries. About halfway through the project I realized I
needed to switch from SQLite to PostgreSQL, and changing databases was
fairly painless because Caqti supports both.

I also made use of Caqti's features for dealing with custom column
types. Caqti does not have built-in support for JSON columns, but
adding a custom column type to handle this was straightforward:

```
type readings = float option array [@@deriving yojson]

let sql_readings =
  let encode (a: readings) =
    Ok (a |> yojson_of_readings |> Yojson.Safe.to_string)
  in
  let decode text =
    Ok (text |> Yojson.Safe.from_string |> readings_of_yojson)
  in
  T.(custom ~encode ~decode string)
```

In my case, the JSON that I needed to store consisted of arrays of
floating point numbers, so building the custom type was simply a
matter of connecting Yojson and Caqti in the right way.

## Discussion

Ever since I started building web applications in Python, I've thought
of an API server as a big function that transforms requests into
responses, with any nontrivial state residing in databases or services
like S3. Dream provides a modern web framework that matches my mental
model for how a web server should work.

Web programming in OCaml "feels" a bit different than working in
Python. In Python it's possible to get something running quickly, but
it's also easy to forget corner cases and introduce defects that have
to be addressed later in the application's lifecycle. An OCaml project
requires some up-front investment, but this investment pays off later
in several ways. First, fast feedback from the compiler (together with
editor integrations like `merlin` and `tuareg`) helped me to identify
issues earlier. `Yojson` made it simple to enforce that JSON requests
and responses adhered to a fixed schema, and helped me process inputs
more systematically. OCaml made refactoring safe and easy, so that I
could confidently adapt my design as I introduced new requirements. In
the right context, I think the advantages of using OCaml could
significantly reduce the total lifecycle costs of maintaining many web
applications without reducing the pace of new development.

## References

I found the resources below helpful for working on this project:

- The Dream [API docs](https://aantron.github.io/dream/) set a high
  standard for readability and helped me quickly get up to speed with
  the framework.
- This [section](https://github.com/aantron/dream/tree/master/example)
  of the Dream repo has excellent examples, both for working with the
  framework and deploying it.
- I referred to Bobby Priambodo's [blog
  posts](https://medium.com/@bobbypriambodo/interfacing-ocaml-and-postgresql-with-caqti-a92515bdaa11)
  about interfacing Caqti and PostgreSQL as I wrote the models in my project.
- The Caqti
  [docs](https://paurkedal.github.io/ocaml-caqti/index.html),
  especially for `Caqti_type` and `Caqti_request` were helpful as I
  was writing queries.
- There is also an
  [example](https://github.com/paurkedal/ocaml-caqti/blob/master/tests/bikereg.ml)
  in the Caqti repo that is worth looking through.
- The README on
  [ppx_yojson_conv](https://github.com/janestreet/ppx_yojson_conv) had
  helpful examples that I referred to while writing my own
  JSON-related types.

## Feedback

If you ended up looking through the source code for my API, let me
know how what you thought! I'm interested in adding more tutorial
resources to the OCaml ecosystem, so feel free to post a PR or issue
to
[sensors](https://github.com/jsthomas/sensors)
if you have ideas about how to make these resources better.
