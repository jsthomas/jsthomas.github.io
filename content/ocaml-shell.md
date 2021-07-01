Title: Let's write a shell in OCaml!
Date: 2021-07-01
Category: OCaml
Slug: ocaml-shell
Summary: A user experience report about writing a simple shell in OCaml

This Summer I'm studying OCaml and systems programming at the [Recurse
Center](https://www.recurse.com/). Currently I'm reading the
delightful book [_Operating Systems: Three Easy
Pieces_](https://pages.cs.wisc.edu/~remzi/OSTEP/) by Remzi
Arpaci-Dusseau and Andrea Arpaci-Dusseau. Besides great exposition,
the book includes several interesting projects, one of which is to
[write a
shell](https://github.com/remzi-arpacidusseau/ostep-projects/tree/master/processes-shell).

The project materials, a set of shell scripts that define tests, are
language agnostic. I believe the authors intended for students to use
C, but I worked through the exercise in OCaml; you can find the final
result [in this
repo](https://github.com/jsthomas/simple-ocaml-shell). This blog post
is a short experience report; if you're interested in working on a
beginner OCaml project, hopefully it can provides some useful
scaffolding for your studies.

## Shell features

The shell I built (`osh`) has a somewhat limited feature set. It:

- Allows several commands to be run in parallel (e.g. `program1 arg1 &
  program2 arg2 arg3`)

- Supports simple output redirection (e.g. `echo "hello" >
  hello.txt`). Both `stdout` and `stderr` go to the same file.

- Has three builtin functions, `cd`, `exit`, and `path`. `path` allows
  you to define a list of directories to search for executables; we
  need this because environment variables aren't supported.

Other niceties, like tab completion and pipes, aren't supported. To
facilitate testing, the shell can run in a batch mode (`osh <my file
of commands>`) as well as an interactive mode. A final simplifying
assumption is that `osh` only provides a basic error message when
inputs are malformed.

## Concepts

There are three main topics I studied while working on this project:

1. The `Unix` module, especially `fork` and
	`execv`. [This
	page](https://ocaml.github.io/ocamlunix/ocamlunix.html), from
	Xavier Leroy and Didier Rémy, was helpful for getting up to
	speed. The man-pages were also useful.

2. The [`Stream`](https://ocaml.org/api/Stream.html) module. Streams
   in OCaml are roughly analogous to generators in Python; they
   allowed me to use a single type (a `string Stream.t`) to represent
   commands coming from an interactive session or a batch file.

3. The [Angstrom](https://github.com/inhabitedtype/angstrom)
   parser-combinator library. I used this library to determine whether
   a given line of user input is well formed.

I suspect you could implement the parser without Angstrom, if you
really wanted to. I wanted to learn more about this library, and this
project seemed like a good place to try it out.

Although I previously worked through some simple monadic parser
exercises in Haskell, I struggled the most with Angstrom. Reading one
of the main [mli
files](https://github.com/inhabitedtype/angstrom/blob/master/lib/angstrom.mli)
seemed to be the best way to get an overview of the combinators the
library provides. I also spent a fair amount of time experimenting in
`utop` as I put my parser together.

## Steps

Here is a rough outline for how I built my shell.

First, I defined a main function that would fetch a line of text from
`stdin` and echo it back to the user. Then I added the ability to
represent either interactive or batch input with a `Stream`:

```ocaml
let prompt_stream =
  let f _ =
    Printf.printf "osh> ";
    Some (read_line ()) in
  Stream.from f


let file_stream filename =
  let in_channel = open_in filename in
  let f _ =
    try
      Some (input_line in_channel)
    with End_of_file ->
      close_in in_channel;
      None
  in
  Stream.from f
```

It's useful to do this part as early as possible, since batch input
allows you to run the tests.

Once I could get `osh` to fail all 22 test cases, I started adding the
simpler built-in commands `cd` and `exit`. (Note `./test-osh.sh -c`
will run all 22 tests, without stopping at the first one that fails.)

My first version of `main` just treated user input as `string list`:
```ocaml
let rec main stream =
  let parse text = String.split_on_char ' ' text in
  let process text =
    match parse text with
    | [] -> main stream  (* Empty lines should just be treated as no-ops. *)
    | [""] -> main stream
    | ["exit"] -> exit 0
    | ["cd"; x] -> Unix.chdir x
    | "cd":: _ -> print_error ()
    | x::xs ->
      match Unix.fork () with
      | 0 -> (* Child *)
        Unix.execv x (Array.of_list xs)
      | child_pid -> (* Parent *)
        let _ = Unix.waitpid [] child_pid
        in ()
  in
  Stream.iter process stream
```

This worked well enough for running simple commands like `/usr/bin/ls
-lah`. In order to get output redirection and `&` to work, I needed to
upgrade the program's parsing capabilities. I switched from
representing user input with a `string list` to a variant type:

```ocaml
type exec = {
  executable: string;
  arguments: string list;
  output: string option;
}

type line =
  | NoOp
  | ChangeDirectory of string
  | PathChange of string list
  | Executable of exec list
  | Quit
```

I found the OCaml compiler (and its emacs integrations, `merlin` and
`tuareg`) very helpful for refactoring. When I revised my types to
make them better reflect the data I wanted to model, type errors
identified all of the places I needed to update. At this point, I
introduced an Angstrom parser and re-implemented support for `cd`,
`exit`, and `path`. That allowed me to get familiar with the parser
combinators `*>`, `many`, and `choice`, before attempting the more
complicated parsers needed to support `&` and `>`.

The type system protected me from a number of silly mistakes, but it
wasn't a silver bullet. I spent an hour confused about why one of my
parsers would go into an infinite loop before realizing I needed to
use `many1` instead of `many`. I think this is the sort of mistake I
would learn to avoid if I spent more time working with Angstrom.

## Discussion

As I worked through this project, I started to appreciate how OCaml
chooses "good defaults" for my code (especially immutable data)
without forbidding me from working in an imperative mode when I need
to.

For example, I found that the function responsible for running a child
process was most natural to express with imperative language features:

```ocaml
let run_executable path {executable; arguments; output} =
  let full_paths = List.map (fun p -> p ^ "/" ^ executable) path in
  let executables = List.append full_paths [executable] in
  let present = List.filter executable_present executables in

  match present with
  | [] -> print_error (); None
  | x :: _ ->
    match Unix.fork () with
    | 0 -> (* Child *)
       let out = match output with
         | Some filename -> Unix.openfile filename [Unix.O_TRUNC; Unix.O_WRONLY; Unix.O_CREAT ] 0o640
         | None -> Unix.stdout
       in
       let err = match output with
         | None -> Unix.stderr
         | _ -> out
       in
       Unix.dup2 out Unix.stdout;
       Unix.dup2 err Unix.stderr;
       Unix.execv x @@ Array.of_list @@ executable::arguments;
    | child_pid -> (* Parent *)
      Some child_pid
```

Writing this way made it easy for me to switch between C and OCaml; in
both languages, we follow a pattern of calling `fork`, then `execv` in
the child process. The fact that I can easily re-use my knowledge of
the UNIX APIs across different programming languages is one of the
main reasons I'm excited to learn more systems programming concepts!

Variants and pattern matching are features I miss when working in
languages like Python. These features make it so easy to look at a
function like:

```ocaml
let main stream =
  let path = ref ["/bin"] in
  let process text =
    match Parser.parse_line text with
    | Error _ -> print_error ()
    | Ok (NoOp) -> () (* Empty lines should just be treated as no-ops. *)
    | Ok (Quit) -> exit 0
    | Ok (ChangeDirectory x) -> change_directory x
    | Ok (PathChange paths) ->
      let cwd = Unix.getcwd () in
      path := List.map (amend_path cwd) paths
    | Ok (Executable execs) -> run_executables !path execs
  in
  Stream.iter process stream
```

and quickly understand all of the different commands `osh` supports.

Although it took me some time to get up and running with Angstrom, I
strongly prefer working with parser combinators to writing an
imperative parser (as I've had to do in Python and Java). Angstrom
makes it easy to build up small parsers and test them in isolation
before composing them into the larger parser you really need. If I
planned to develop a shell with more features, I would probably break
`Parser` out into its own file with separate unit tests.

## Feedback

If you give this project a try, let me know how it turned out! I'm
interested in adding more tutorial resources to the OCaml ecosystem,
so feel free to post a PR or issue to
[simple-ocaml-shell](https://github.com/jsthomas/simple-ocaml-shell)
if you have ideas about how to make these resources better.
