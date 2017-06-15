Title: On the Implementation of Map
Date: 2017-06-06
Category: OCaml, Profiling
Slug: map-comparison
Summary: A comparison of different implementations of map in OCaml
Status: draft

`Map` is one of the first higher-order functions I remember
encountering when I learned some rudimentary functional programming
topics as an undergraduate. More recently I began learning OCaml. The
`map`
[implementation](https://github.com/ocaml/ocaml/blob/2691c40f2ff9bc34912db39bc1f17045c9241473/stdlib/list.ml#L80-L82)
I found in the standard library was the textbook definition I was
expecting

    let rec map f = function
        [] -> []
      | a::l -> let r = f a in r :: map f l

but I was surprised to learn there are actually several
implementations of `map`, with different characteristics:

* The implementation above (which I'll refer to as `stdlib`) is not
  *tail recursive*, so it takes space on the stack proportional to the
  *length of the input list. For long enough lists, this causes a
  *stack overflow.

* One can instead write a tail recursive version that takes up
  constant space on the stack, at the cost of an additional list
  traversal.

* The package `batteries` features a more imperative
  [implementation](https://github.com/ocaml-batteries-team/batteries-included/blob/c10c65a203a7590b15b9a370f66e8c2884817428/src/batList.mlv#L163-L173).

* The package `base` has an
  [implementation](https://github.com/janestreet/base/blob/f10483e957206dc6b656a28ffec667d8b068c149/src/list.ml#L311-L345)
  that treats short lists and long lists differently
  (somewhat like loop unrolling).

* The `containers` package features yet another
[implementation](https://g
ithub.com/c-cube/ocaml-containers/blob/d659ba677e3dbd95430f59b3794ac2f2a5677d61/src/core/CCList.ml#L20-L37)
that handles very short lists separately and defaults to tail
recursion for long lists.

Given all of these different ways to `map`, I wanted to know:

* Which version is the fastest?

* How much speed does one lose using the safer tail recursive version?

Part of my motivation to write this post arose from
[this discussion](https://github.com/ocsigen/lwt/pull/347) of a pull
request, which proposes the default `map` implementation in `lwt`
should be tail recursive. After reading all of the comments, I wanted
to develop some experiments that would convince me whether a tail
recursive `map` really is too slow to be used.

# Experimental Setup

In 2014, Jane Street introduced a
[library](https://github.com/janestreet/core_bench) for
microbenchmarking called `core_bench`. As they explain [on their
blog](https://blogs.janestreet.com/core_bench-micro-benchmarking-for-ocaml/),
`core_bench` is intended to measure the performance of small pieces of
OCaml code.

There are a couple benefits to measuring map implementations with
`core_bench`.

1. The library makes it easy to track both time and use of the heap.

2. Once you specify your test, `core_bench` automatically provides
   many [command line
   options](https://github.com/janestreet/core_bench/wiki/Getting-Started-with-Core_bench)
   to help you present your test data in different ways.

3. The library uses statistical techniques (bootstrapping and linear
   regression) to reduce many runs worth of data to a small number of
   meaningful performance metrics.

I wrote
[this program](https://github.com/jsthomas/ocaml-analysis/blob/master/map/maptest.ml)
to compare performance between the five implementations I described
above. Specifically:

* I tested each algorithm against lists of lengths $N=10^2, 10^3, 10^4$ and
  $10^5$. On my system, $N=10^5$ was the highest power of 10 for which
  the naive implementation did not fail due to a stack overflow.
* Each list consisted of integer elements (all 0), and the function
  mapped onto the list simply added one to each element.
* I ran these tests on a Lenovo X220, Intel Core i5-2520M CPU (2.50GHz ×
  4 cores), and 4GB RAM.
* I used the OCaml 4.03.0 compiler, and compiled to native code
  without using `flambda`. ([This
  makefile](https://github.com/jsthomas/ocaml-analysis/blob/master/map/makefile)
  gives the full specifications.)

# Results

For each list size, `core_bench` produces a table with several metrics besides time:

* `mWd` : Words allocated on the minor heap.
* `mjWd` : Words allocated on the major heap.
* `Prom` : Words promoted from minor to major heap.

The library also allows us to produce 95% confidence intervals and
$R^2$ values for the time estimates.

**Map Benchmark, N = 100**
```
┌────────────┬──────────┬──────────┬───────────────┬─────────┬──────────┬──────────┬────────────┐
│ Name       │ Time R^2 │ Time/Run │        95% ci │ mWd/Run │ mjWd/Run │ Prom/Run │ Percentage │
├────────────┼──────────┼──────────┼───────────────┼─────────┼──────────┼──────────┼────────────┤
│ tail rec.  │     1.00 │ 732.23ns │ -0.21% +0.23% │ 609.01w │    0.53w │    0.53w │    100.00% │
│ containers │     1.00 │ 427.59ns │ -0.12% +0.13% │ 304.03w │    0.17w │    0.17w │     58.40% │
│ batteries  │     1.00 │ 578.28ns │ -0.14% +0.15% │ 309.01w │    0.35w │    0.35w │     78.98% │
│ base       │     1.00 │ 419.16ns │ -0.21% +0.27% │ 304.03w │    0.16w │    0.16w │     57.24% │
│ stdlib     │     1.00 │ 614.10ns │ -0.24% +0.26% │ 304.01w │    0.17w │    0.17w │     83.87% │
└────────────┴──────────┴──────────┴───────────────┴─────────┴──────────┴──────────┴────────────┘
```
**Map Benchmark, N = 1000**
```
┌────────────┬──────────┬──────────┬───────────────┬─────────┬──────────┬──────────┬────────────┐
│ Name       │ Time R^2 │ Time/Run │        95% CI │ mWd/Run │ mjWd/Run │ Prom/Run │ Percentage │
├────────────┼──────────┼──────────┼───────────────┼─────────┼──────────┼──────────┼────────────┤
│ tail rec.  │     1.00 │   8.82us │ -0.22% +0.27% │  6.01kw │   52.09w │   52.09w │    100.00% │
│ containers │     1.00 │   5.08us │ -0.22% +0.26% │  3.00kw │   17.26w │   17.26w │     57.62% │
│ batteries  │     0.98 │   6.79us │ -1.45% +1.88% │  3.01kw │   34.71w │   34.71w │     76.96% │
│ base       │     1.00 │   4.96us │ -0.18% +0.19% │  3.00kw │   17.08w │   17.08w │     56.27% │
│ stdlib     │     0.99 │   6.87us │ -0.99% +1.36% │  3.00kw │   17.25w │   17.25w │     77.84% │
└────────────┴──────────┴──────────┴───────────────┴─────────┴──────────┴──────────┴────────────┘
```

**Map Benchmark, N = 10,000**
```
┌────────────┬──────────┬──────────┬───────────────┬─────────┬──────────┬──────────┬────────────┐
│ Name       │ Time R^2 │ Time/Run │        95% CI │ mWd/Run │ mjWd/Run │ Prom/Run │ Percentage │
├────────────┼──────────┼──────────┼───────────────┼─────────┼──────────┼──────────┼────────────┤
│ tail rec.  │     1.00 │ 200.15us │ -0.27% +0.29% │ 60.01kw │   5.40kw │   5.40kw │    100.00% │
│ containers │     0.98 │ 148.02us │ -1.51% +1.81% │ 48.01kw │   3.05kw │   3.05kw │     73.95% │
│ batteries  │     1.00 │ 134.00us │ -0.46% +0.48% │ 30.01kw │   3.62kw │   3.62kw │     66.95% │
│ base       │     1.00 │ 132.76us │ -0.53% +0.58% │ 44.98kw │   2.66kw │   2.66kw │     66.33% │
│ stdlib     │     1.00 │ 120.09us │ -0.43% +0.48% │ 30.00kw │   1.79kw │   1.79kw │     60.00% │
└────────────┴──────────┴──────────┴───────────────┴─────────┴──────────┴──────────┴────────────┘
```

**Map Benchmark, N = 100,000**
```
┌────────────┬──────────┬──────────┬───────────────┬──────────┬──────────┬──────────┬────────────┐
│ Name       │ Time R^2 │ Time/Run │        95% CI │  mWd/Run │ mjWd/Run │ Prom/Run │ Percentage │
├────────────┼──────────┼──────────┼───────────────┼──────────┼──────────┼──────────┼────────────┤
│ tail rec.  │     0.99 │  10.83ms │ -1.81% +1.61% │ 600.02kw │ 414.00kw │ 414.00kw │     99.85% │
│ containers │     0.99 │  10.83ms │ -1.73% +1.97% │ 588.02kw │ 405.39kw │ 405.39kw │     99.84% │
│ batteries  │     0.99 │   7.13ms │ -1.13% +1.05% │ 300.02kw │ 300.35kw │ 300.35kw │     65.77% │
│ base       │     0.99 │  10.85ms │ -1.93% +1.92% │ 584.99kw │ 399.21kw │ 399.21kw │    100.00% │
│ stdlib     │     0.99 │   6.57ms │ -1.24% +1.19% │ 300.01kw │ 173.43kw │ 173.43kw │     60.56% │
└────────────┴──────────┴──────────┴───────────────┴──────────┴──────────┴──────────┴────────────┘
```

I noticed several things about in the data above:

* The tail recursive implementation is consistently slowest. (In the
  final test `base`, `containers` and the tail recursive version all
  appear to be equally slow.) This makes sense, because both libraries
  default to a tail recursive implementation for long lists.

* For short lists, `base` and `containers` are quite fast, possibly
  due to the "loop unrolling" (special cases for short lists) in their
  definitions.

* We can see from the `mWd` and `mjWd` columns that the tail recursive
  implementation uses the most heap space, as we would expect.

* As we increase the size of the list, `stdlib` gets faster relative
  to `stdlib` (from 83% to 60%); I suspect this can be attributed to
  the cost of garbage collections.

# Conclusions

The data above suggests two findings:

1. The naive tail recursive implementation is significantly slower
   than the stack-based standard library implementation.

2. There is a benefit to using a more complicated "hybrid"
   implementation that treats very short lists with special cases, and
   reverts to tail recursion for long lists.

We can see in the $N = 100$ data that the `base` and `containers`
implementations are significantly faster than `stdlib`, but unlike
`stdlib` they cannot cause a stack overflow. Given that these
implementations are safer *and* faster for short lists, it seems
reasonable to prefer them.

# Discussion

A follow up question to this analysis, in the context of the
discussion of `Lwt.map` is: "How significant is the cost of `map`
compared to other operations?" To partially address this, I wrote
[another program](https://github.com/jsthomas/ocaml-analysis/blob/master/map/bufftest.ml)
that measures how long it takes to write 4096 bytes to a Unix pipe
using `Lwt.write`, and then read it back using `Lwt.read`. Using
`core_bench`, I found:

**Unix Pipe Write Benchmark**
```
┌─────────┬──────────┬───────────────┬─────────┬────────────┐
│Time R^2 │ Time/Run │          95ci │ mWd/Run │ Percentage │
├─────────┼──────────┼───────────────┼─────────┼────────────┤
│    1.00 │ 893.33ns │ -0.16% +0.18% │  56.00w │    100.00% │
└─────────┴──────────┴───────────────┴─────────┴────────────┘
```
It seems reasonable to estimate that `Lwt.map` would primarily be
applied to IO operations like the ones in this experiment. With that
premise, the data suggests that the ammortized cost per element of
applying the slowest map implementation (`tail rec.`) is about 0.82%
of the cost of one 4KB read/write operation on a unix pipe. Overall, I
take this to mean that the implementation of `map` shouldn't be a
significant concern; the real cost is performing IO. In light of that,
it seems preferable to use an implementation that cannot fail due to a
stack overflow.
