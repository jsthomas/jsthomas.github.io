Title: Full Stack Web Development in OCaml (Part 1)
Date: 2021-07-11
Category: OCaml
Slug: ocaml-full-stack-pt-1
Summary: A multi-part series about web application development in OCaml

This is the first blog post in a series; I've started a multi-week
project to explore the state of full stack web development in
OCaml. This post outlines the background and goals for the project.

# Background

I've been building web applications in Python since 2015. Most of the
projects I've worked on have had a machine learning or analytics
component. Python was advantageous for this type of work because its
diverse ecosystem of third party libraries allowed me to solve many
different problems fairly well. I could write analytics processes with
`numpy` and `pandas`, build a REST API to serve the results in
`pyramid`, and manage supporting cloud services with `boto`.

Several (relatively) recent additions to the OCaml ecosystem make me
think that OCaml might be a good fit for my workflow:

- The [Dream](https://aantron.github.io/dream/) web
framework, introduced in May, has excellent documentation and support
for many modern web development patterns (GraphQL, WebSockets, etc.).

- There are now several tools (for example
[`js_of_ocaml`](https://github.com/ocsigen/js_of_ocaml) and
[rescript](https://rescript-lang.org/)) that allow a frontend to be
written in OCaml (or a language very close to OCaml).

- The [owl](https://ocaml.xyz/) project provides scientific computing
primitives for mathematics, statistics, and machine learning, allowing
me to replace `numpy`/`pandas` in my current workflow.

I think there may be a number of benefits to adopting OCaml:

1. *Type Safety*: The OCaml compiler allows me to write code without
   many type annotations, but still reap the benefits of a strong type
   system. Python tools like `mypy` and `pyre` do some of this, but
   (by design) aren't as rigorous as the checks imposed by the OCaml
   compiler.

2. *Ease of Refactoring*: Changing requirements are a fact of life in
   software engineering. Type safety means that it's easier to modify
   existing business logic and dependencies without breaking things.

3. *Speed*: OCaml's performance profile is similar to C++. Because
   Python is interpreted, it's hard to get comparable performance
   without re-writing parts of your application in C/C++.

4. *One common language across the application*: Context switching
   between javascript and python is certainly possible, but I've often
   wondered if using a single language on the frontend and backend
   would be more efficient.

These are just hypotheses. Though I've looked at existing [experience
reports](https://roscidus.com/blog/blog/2014/06/06/python-to-ocaml-retrospective/),
it's hard to know whether a particular tool chain is a good fit
without building nontrivial applications with it. So, I've decided to
build an application with a frontend, backend, and analytics
component, all in OCaml. As I go, I'll write up blog posts about what
worked and what didn't.

# Project Description

I'm building a simple web app called _Sensors_. A "sensor" is anything
that generates a series of floating point values over time. A weather
station reading wind speed every minute is one example of a sensor. A
traffic camera that reports how many cars passed in a given hour is
another. If you've used Datadog's features for predicting trends in
CPU or disk use, then you have some idea of how time series analysis
can fit into a larger application.

The idea of the app is pretty simple:

- Users log in to the application to manage
  (create/read/update/delete) their sensors.
- Each sensor comes with an API key that grants access to an endpoint
  for uploading data, formatted as JSON.
- The frontend allows users to plot time series data, combine existing
  time series to form new ones (for example, adding two streams of
  values together), and run different forecasting algorithms on their
  data.

From a technical standpoint, the application has three parts:

1. A REST API, written using `Dream`. This server will be responsible
   for managing data in a PostgreSQL database.

2. A frontend developed with `rescript`. This part of the application
   will have to utilize existing libraries for plotting sensor data.

3. A simple analytics system that uses standard algorithms for
   generating time series forecasts.

If time permits, I may also build a simple IoT device that uses OCaml
to upload data to the service. Since the purpose of this project is to
assess a collection of tools, there are some topics I'm intentionally
going to omit:

- I'm not going to consider how to deploy the application. It isn't a
  "product" and I won't worry about integrating it with some cloud
  environment, like AWS or Google Cloud.

- Since this won't be deployed on the internet, I'm not going to spend
  much time on security concerns, beyond stubbing in simple passwords
  and API keys. (This isn't my area of expertise anyway.)

- I'm also not going to worry about some database management concerns,
  like how to perform migrations. There are plenty of mature tools for
  this and choosing one of them doesn't (in my experience) have much
  impact on day to day development work on the app itself.

With all of that out of the way, let's get started using OCaml to
[build a REST API]({filename}/ocaml-fullstack-pt2.md)!
