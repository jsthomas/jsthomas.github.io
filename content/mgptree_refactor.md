Title: Refactoring Python Code
Date: 2017-05-01
Category: Python, Projects, Refactoring
Slug: mgptree-refactor
Summary: Refactoring some python code from many years ago.

Recently, a friend from grad-school asked me about an
[experimental python data visualization tool](https://github.com/jsthomas/mgptree)
I wrote in 2012. Since the code had rotted (to the point that it no
longer worked), and my understanding of python has changed quite a bit
since I originally wrote it, I thought this would be a good
opportunity to write about my current processes for debugging and refactoring.

## What's this supposed to do again?

The premise of the program is pretty simple:

1. The
   [Mathematics Genealogy Project (MGP)](https://www.genealogy.math.ndsu.nodak.edu/)
   lets us search for advisor-advisee relationships between names.

2. We want to take a list of names $L$ and an integer $n$, and look up
   $n$ generations of mathematicians, starting from $L$.

3. Then, we want to render the digraph of advisee-advisor
   relationships using the [`graphviz`](http://graphviz.org/) program
   `dot`.

Looking at this code it's surprising some of the things I did and
didn't know:

1. Prior to 2014, I wasn't in the habit of using virtual environments
   and `pip`. For this project, that's not really a big deal because
   there aren't a lot of dependencies.

2. I wasn't aware of `pylint`. Today, I find that `pylint` makes it a
   lot easier to write clean python and refactor existing code.

Some things that haven't changed:

1. I still think graphviz is really great. It makes plotting directed
   graphs *so* easy, and it's easy to decorate them with a lot of
   metadata.

2. `argparse` makes it easy to write a command line interface that
   works just like other familiar unix tools. I especially like that
   adds `-h` options for displaying help, which are invaluable when
   building a more extensive CLI tool.

## Phase 1: Cleaning up lint issues.

Whenever I'm starting on unfamiliar python code, I like to begin with
`pylint`'s suggestions.

    ```
    ...
    C:384, 4: Invalid method name "extractPersonalData" (invalid-name)
    C:384, 4: Missing method docstring (missing-docstring)
    C:391,11: Do not use `len(SEQUENCE)` as condition value (len-as-condition)
    C:395,11: Do not use `len(SEQUENCE)` as condition value (len-as-condition)
    C:399,11: Do not use `len(SEQUENCE)` as condition value (len-as-condition)
    C:402, 4: Missing method docstring (missing-docstring)
    C:405, 4: Missing method docstring (missing-docstring)
    W:408,12: Unused variable 'name' (unused-variable)

    ---------------------------------------------------------------------
    Your code has been rated at -1.83/10
    ```

Pylint scored my original code -1.83/10. D'oh. It turns out one of the
things I wasn't following in 2012 was PEP8, which means I had a lot of
formatting/whitespace issues. Fixing these, my score rose to
6.94/10.

One thing that I really like about `pylint` is how it dramatically
simplifies finding unused variables in my code. Sometimes, I even use
this to help me refactor more systematically: First I change whatever
lines I planned to simplify, then I let `pylint` confirm that I can
get rid of the variables I'd planned to eliminate. It turns out I had
four unused variables in 430 lines of code, all easy to fix.

Another convention I wasn't following in 2012 is the use of
docstrings. Instead, I was writing big block comments, like:

    :::python
    ################################################################################
    # Procedure: validate_scrape
    #
    # Input: Parser and options objects from optparse
    #
    # Output: A list of well-formed name tuples.
    #
    # Effects: Checks the options object to confirm the inputs are well formed.
    #
    ################################################################################

Now that I work with jupyter and ipython more often, I have a better
appreciation for docstrings. It's really helpful to be able to do
`function_i_dont_remember ?` at a REPL and immediately pull up
documentation without context switching.


## Phase 2: Cleaning up the output.

After fixing documentation, the next issue I wanted to improve was the
script's lack of logging. For some reason, I'd thought it would be a
good idea to send everything directly to `stdout` or `stderr`. I even
added a `verbose` command line flag, and then introduced conditionals
in my code, like:

    :::python
    if OPTIONS.verbose_on:
        sys.stdout.write("Searching MGP for %s, %s, %s.\n" % (last, first, middle))

To simplify this, I introduced the `logging` package with a simple
configuration:

    :::python
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')

which let me write logs at several different levels whose visibility
can be adjusted in the configuration.

## Phase 3: Fixing bugs.

At this point, I'd resolved most of the obvious issues I wanted to
fix, and narrowed down `pylint`'s suggestions to four issues, two of
which were TODOs I'd notice while addressing other issues:

    ************* Module mgptree
    W: 58, 0: TODO: Refactor options to be either completely global or not. (fixme)
    W:158, 0: TODO: Consider refactor here. (fixme)
    W: 36, 4: Using the global statement (global-statement)
    R:208, 0: Too many instance attributes (8/7) (too-many-instance-attributes)

    --------------------------------------------------------------------
    Your code has been rated at 9.77/10

Fixing the whitespace/formatting issues turned out to be a good way to
re-familiarize myself with the code before attempting to fix the
functional issues.

After running `mgptree` on a couple simple examples and looking at the
logs, I realized that the main functional issue was in the function
`fetch_id_num`. This function is supposed to take a tuple of names
(first, middle, and last) and determine the ID number of the
mathematician with that name in the MGP service (if the lookup fails
or returns multiple answers, we return `None`). The function is
supposed to do this by using `requests` to make a POST to the URL
associated with the PHP script that handles users' searches on the MGP
site, and then scraping the resulting reply.

Looking at the MGP website, it didn't appear to be very different from
what I remembered seeing in 2012, so I was puzzled why my scraping
code had stopped working. After running my function a few times in an
`ipython` shell, I realized my main error was my URL. Like a lot of
websites, the math genealogy has moved to HTTPS since 2012. Fixing
that and one other formatting change in the pages' `<title>` section
and my scraping code was working properly again.

## Wrapping Up

Overall, the improvements I made to my script were pretty trivial,
but they illustrate some practices that I think are really helpful for
increasing one's personal productivity:

1. *Restoring an Invariant*: When I don't know what to do next (or
   where to start), I find `pylint` and `nosetests` are great
   guides. Both tools specify an invariant (no lint errors above a
   certain level, all unit tests passing, etc.) that should be
   maintained whenever code gets committed. If the invariant isn't
   satisfied, the next steps are clear: Investigate why, and fix it.

2. *One Thing a Time:* Even though my changes were simple, I made a
   total of 8 commits to get my code back in working order. Each one
   focusses on a single issue I wanted to improve in the code
   (i.e. remove all whitespace lint errors). I find it can be really
   easy to start "improving" two or three issues at the same time, and
   then do a poor job on all of them (or get stuck). For me, following
   the rule of one issue per commit has been a great way to stay
   organized and break larger problems into manageable pieces.

I can see a couple of areas I might want to improve in the future. It
would be nice to to store scraped data in an `sqlite` database, which
might simplify computing other graph-based presentations of the
dataset (for example, finding all of the students descended from a
particular mathematician). It might also be cool to convert this to a
django or flask app, so that people unfamiliar with the command line
can generate their own graphs.
