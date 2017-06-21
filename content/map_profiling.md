Title: Microbenchmarking Implementations of Map in OCaml
Date: 2017-06-06
Category: OCaml, Profiling
Slug: map-comparison
Summary: A comparison of different implementations of map in OCaml


`Map` is one of the first higher-order functions I remember
encountering when I learned some rudimentary functional programming
topics as an undergraduate. More recently I began learning OCaml. The
`map`
[implementation](https://github.com/ocaml/ocaml/blob/2691c40f2ff9bc34912db39bc1f17045c9241473/stdlib/list.ml#L80-L82)
I found in the standard library was the textbook definition I was
expecting

```ocaml
let rec map f = function
    [] -> []
  | a::l -> let r = f a in r :: map f l
```
but I was surprised to learn there are actually several
implementations of `map` in the OCaml ecosystem. I wanted to know more
about these different implementations and their performance
characteristics. This article summarizes what I learned.

Part of my motivation to write this post arose from
[this discussion](https://github.com/ocsigen/lwt/pull/347) of a pull
request that proposes the default `map` implementation in `lwt` should
be tail recursive. After reading all of the comments, I wanted to
develop experiments that would convince me whether this was a good
idea.

# Introduction

Since I'll introduce several versions of `map`, I'll refer to the
implementation above as `stdlib`. An important aspect of this version
is that it isn't *tail recursive*. A tail recursive function uses
recursion in a specific way; it only calls itself as the final
operation in the function. In OCaml, tail recursive functions get the
benefit of tail-call optimization so that they only use one frame on
the stack. In contrast, the `stdlib` implementation takes space on the
stack proportional to the length of the input list. For long enough
lists, this causes a stack overflow.

We can make a basic tail-recursive version of `map` by composing two
standard library functions that are tail recursive: `List.rev_map`
(which creates the output of `map`, but in reversed order) and
`List.rev` which reverses lists. I'll call this naive implementation
`ntr` (naive tail recursive). Compared to `stdlib`, `ntr` allocates
twice as much space on the heap (one list for the output of
`List.rev_map`, and a second equally long list for `List.rev`) and
spends additional time performing a list traversal. The benefit is
that with this implementation, calling `map` on a long list won't
result in a stack overflow.

As we'll see later in the Results section, the naive tail recursive
implementation is, overall, slower than the `stdlib`
implementation. However, there are some optimizations we can apply to
improve the performance of both versions.

The first trick I call "unrolling". Similar to
[loop unrolling in procedural languages](https://en.wikipedia.org/wiki/Loop_unrolling),
the idea is to use cases to `map` on groups of list elements so fewer
function calls are needed to complete the work. For example, an
unrolled version of `stdlib` looks like:

```ocaml
let rec map f l =
  match l with
  | [] -> []
  | [x1] ->
    let f1 = f x1 in
    [f1]
  | [x1; x2] ->
    let f1 = f x1 in
    let f2 = f x2 in
    [f1; f2]
  | x1 :: x2 :: x3 :: tl ->
    let f1 = f x1 in
    let f2 = f x2 in
    let f3 = f x3 in
    f1 :: f2 :: f3 :: map tl
```

We get to choose how many elements to unroll (here I picked 3); some
profiling is needed to decide the most appropriate number.

The second trick I call "hybridizing". The `stdlib` version is faster,
but isn't safe for long lists. The tail recursive implementation is
slow, but safe for all lists. When we "hybridize" the two, we use the
faster version up to some fixed number of elements (e.g. 1000), and
then switch to the safe version for the remainder of the list.

These two optimizations are useful for understanding the
implementations of `map` we find in other libraries. For example, both
[`base`](https://github.com/janestreet/base/blob/f10483e957206dc6b656a28ffec667d8b068c149/src/list.ml#L311-L345)
and
[`containers`](https://github.com/c-cube/ocaml-containers/blob/d659ba677e3dbd95430f59b3794ac2f2a5677d61/src/core/CCList.ml#L20-L37)
use an unrolled `stdlib`-style `map`, hybridized with an
`ntr`-style `map`.

Looking at `ntr`, one might ask: Is it strictly necessary to use
additional heap space to get the implementation to be tail recursive?
The answer is no. The `batteries` package
[implements `map`](https://github.com/ocaml-batteries-team/batteries-included/blob/c10c65a203a7590b15b9a370f66e8c2884817428/src/batList.mlv#L163-L173)
so that the work is done by a single tail recursive function, creating
one new list on the heap. To achieve this, the implementation uses
mutable state and casting to avoid a second list traversal
(specifically,
[here](https://github.com/ocaml-batteries-team/batteries-included/blob/c10c65a203a7590b15b9a370f66e8c2884817428/src/batList.mlv#L69)).

As with any optimization, one makes tradeoffs between elegance,
performance, and the language features one considers acceptable to
use. I wanted to know:

* Which version is the fastest in practice?

* How much speed does one lose using the safer tail recursive version?

Both `base` and `containers` decided to hybridize with an `ntr`-style
`map` for safety. But the `batteries` implementation is also robust to
stack overflow. That led to one final question:

* How fast is an unrolled `stdlib`-style `map` hybridized with a
  `batteries`-style `map`?

# Experimental Setup

In 2014, Jane Street introduced a
[library](https://github.com/janestreet/core_bench) for
microbenchmarking called `core_bench`. As they explain
[on their blog](https://blogs.janestreet.com/core_bench-micro-benchmarking-for-ocaml/),
`core_bench` is intended to measure the performance of small pieces of
OCaml code. This library helps developers to better understand the
cost of individual operations, like `map`.

There are a couple benefits to measuring `map` implementations with
`core_bench`.

1. The library makes it easy to track both time and use of the heap.

2. Once you specify your test, `core_bench` automatically provides
   many [command line
   options](https://github.com/janestreet/core_bench/wiki/Getting-Started-with-Core_bench)
   to help you present your test data in different ways.

3. The library uses statistical techniques (bootstrapping and linear
   regression) to reduce many runs worth of data to a small number of
   meaningful performance metrics that account for the amortized cost
   of garbage collection and error introduced by system activity.

I wrote
[this program](https://github.com/jsthomas/ocaml-analysis/blob/master/map/maptest.ml)
to compare performance between the six implementations I described
above. The program includes the batteries-hybrid I described above,
which I'll refer to as `batt-hybr`. Other test details:

* I tested each algorithm against lists of lengths $N=10^2, 10^3,
  10^4$ and $10^5$. On my system, $N=10^5$ was the highest power of 10
  for which the `stdlib` implementation did not fail due to a stack
  overflow.
* Each list consisted of integer elements (all 0), and the function
  mapped onto the list simply added one to each element.
* I ran these tests on a Lenovo X220, Intel Core i5-2520M CPU (2.50GHz ×
  4 cores), with 4GB RAM.
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
│ Name       │ Time R^2 │ Time/Run │          95ci │ mWd/Run │ mjWd/Run │ Prom/Run │ Percentage │
├────────────┼──────────┼──────────┼───────────────┼─────────┼──────────┼──────────┼────────────┤
│ ntr        │     1.00 │ 741.20ns │ -0.23% +0.22% │ 609.01w │    0.53w │    0.53w │    100.00% │
│ containers │     1.00 │ 439.55ns │ -0.64% +0.67% │ 304.03w │    0.17w │    0.17w │     59.30% │
│ batteries  │     1.00 │ 581.65ns │ -0.14% +0.16% │ 309.01w │    0.35w │    0.35w │     78.47% │
│ base       │     1.00 │ 438.63ns │ -0.19% +0.20% │ 304.03w │    0.16w │    0.16w │     59.18% │
│ stdlib     │     1.00 │ 610.45ns │ -0.10% +0.11% │ 304.01w │    0.17w │    0.17w │     82.36% │
│ batt-hybr  │     1.00 │ 426.76ns │ -0.15% +0.17% │ 304.03w │    0.17w │    0.17w │     57.58% │
└────────────┴──────────┴──────────┴───────────────┴─────────┴──────────┴──────────┴────────────┘
```

**Map Benchmark, N = 1000**
```
┌────────────┬──────────┬──────────┬───────────────┬─────────┬──────────┬──────────┬────────────┐
│ Name       │ Time R^2 │ Time/Run │          95ci │ mWd/Run │ mjWd/Run │ Prom/Run │ Percentage │
├────────────┼──────────┼──────────┼───────────────┼─────────┼──────────┼──────────┼────────────┤
│ ntr        │     1.00 │   8.84us │ -0.14% +0.15% │  6.01kw │   52.08w │   52.08w │    100.00% │
│ containers │     1.00 │   5.07us │ -0.13% +0.15% │  3.00kw │   17.23w │   17.23w │     57.34% │
│ batteries  │     1.00 │   6.57us │ -0.14% +0.14% │  3.01kw │   34.71w │   34.71w │     74.32% │
│ base       │     1.00 │   4.99us │ -0.20% +0.24% │  3.00kw │   17.08w │   17.08w │     56.44% │
│ stdlib     │     1.00 │   6.84us │ -0.10% +0.10% │  3.00kw │   17.22w │   17.22w │     77.34% │
│ batt-hybr  │     1.00 │   4.96us │ -0.13% +0.13% │  3.00kw │   17.07w │   17.07w │     56.10% │
└────────────┴──────────┴──────────┴───────────────┴─────────┴──────────┴──────────┴────────────┘
```

**Map Benchmark, N = 10,000**
```
┌────────────┬──────────┬──────────┬───────────────┬─────────┬──────────┬──────────┬────────────┐
│ Name       │ Time R^2 │ Time/Run │          95ci │ mWd/Run │ mjWd/Run │ Prom/Run │ Percentage │
├────────────┼──────────┼──────────┼───────────────┼─────────┼──────────┼──────────┼────────────┤
│ ntr        │     0.99 │ 203.11us │ -0.45% +0.53% │ 60.01kw │   5.40kw │   5.40kw │    100.00% │
│ containers │     1.00 │ 144.95us │ -0.50% +0.60% │ 48.01kw │   3.04kw │   3.04kw │     71.37% │
│ batteries  │     1.00 │ 136.87us │ -0.51% +0.63% │ 30.01kw │   3.64kw │   3.64kw │     67.39% │
│ base       │     1.00 │ 130.85us │ -0.34% +0.39% │ 44.98kw │   2.66kw │   2.66kw │     64.42% │
│ stdlib     │     1.00 │ 118.70us │ -0.30% +0.29% │ 30.00kw │   1.80kw │   1.80kw │     58.44% │
│ batt-hybr  │     1.00 │ 106.91us │ -0.42% +0.52% │ 30.01kw │   2.22kw │   2.22kw │     52.64% │
└────────────┴──────────┴──────────┴───────────────┴─────────┴──────────┴──────────┴────────────┘
```

**Map Benchmark, N = 100,000**
```
┌────────────┬──────────┬──────────┬───────────────┬──────────┬──────────┬──────────┬────────────┐
│ Name       │ Time R^2 │ Time/Run │          95ci │  mWd/Run │ mjWd/Run │ Prom/Run │ Percentage │
├────────────┼──────────┼──────────┼───────────────┼──────────┼──────────┼──────────┼────────────┤
│ ntr        │     0.98 │  10.27ms │ -2.39% +2.32% │ 600.02kw │ 411.83kw │ 411.83kw │     94.33% │
│ containers │     0.99 │  10.62ms │ -2.19% +1.83% │ 588.02kw │ 404.91kw │ 404.91kw │     97.61% │
│ batteries  │     1.00 │   7.19ms │ -0.78% +0.79% │ 300.02kw │ 300.35kw │ 300.35kw │     66.02% │
│ base       │     0.99 │  10.88ms │ -1.54% +1.41% │ 584.99kw │ 397.60kw │ 397.60kw │    100.00% │
│ stdlib     │     0.99 │   6.33ms │ -1.08% +1.07% │ 300.01kw │ 171.73kw │ 171.73kw │     58.18% │
│ batt-hybr  │     0.93 │   6.09ms │ -4.30% +4.63% │ 300.02kw │ 285.46kw │ 285.46kw │     55.93% │
└────────────┴──────────┴──────────┴───────────────┴──────────┴──────────┴──────────┴────────────┘
```

A few things I noticed about the data:

* The tail recursive implementation is slow, but not always the
  slowest. In the $N=10^5$ case, `ntr`,`base`, and `containers` show
  similar performance; this makes sense given they have the same
  behavior after a prefix of the list.

* For short lists, `base`, `containers`, and `batt-hybr` are fastest,
  likely because of unrolling.

* We can see from the `mWd` and `mjWd` columns that `ntr` uses the
  most heap space, as we would expect.

* As we increase the size of the list, `stdlib` gets faster relative
  to `ntr`; I suspect this can be attributed to the cost of garbage
  collection.

* Overall, `batt-hybr` appears to have the best performance (though in
  the $N=10^5$ case, the confidence interval is large enough that we
  can't conclude `batt-hybr` is faster than `stdlib`, and the $R^2$
  value is a bit low).

# Conclusions

The data above suggest three main findings:

1. The stack-based standard library implementation of `map` is faster
   than the naive tail recursive implementation, taking about 60-80%
   of the time to do the same work depending on the size of the list.

2. There are clear benefits to both unrolling and
   hybridizing. Hybridizing lets us take an implementation that
   performs well on long lists (`batteries`), and make it even better
   by combining it with one that's fast on short lists, to produce
   `batt-hybr`.

3. Overall, the data show we don't have to give up safety (resistance
   to stack overflow) to get better performance. A tail recursive
   implementation can be quite competitive, albeit more complex.

# Discussion

A follow up question to this analysis, in the context of the
discussion of `Lwt_list.map_p` is: "How significant is the cost of
`map` compared to other operations?" To partially address this, I
wrote
[another program](https://github.com/jsthomas/ocaml-analysis/blob/master/map/bufftest.ml)
that measures how long it takes to write 4096 bytes to a Unix pipe
using `Lwt_unix.write`, and then read it back using `Lwt_unix.read`. Using
`core_bench`, I found:

**Unix Pipe Read/Write Benchmark**
```
┌─────────┬──────────┬───────────────┬─────────┬────────────┐
│Time R^2 │ Time/Run │          95ci │ mWd/Run │ Percentage │
├─────────┼──────────┼───────────────┼─────────┼────────────┤
│    1.00 │ 893.33ns │ -0.16% +0.18% │  56.00w │    100.00% │
└─────────┴──────────┴───────────────┴─────────┴────────────┘
```

It seems reasonable to estimate that `Lwt_list.map_p` would primarily
be applied to IO operations like the ones in this experiment. In that
case, the data suggest the cost per element of applying the slowest
`map` implementation (`ntr`) is about 0.82% of the cost of one 4KB
read/write operation on a unix pipe. In the context of `Lwt`, it seems
reasonable to conclude the implementation of `map` isn't a significant
concern; the real cost is performing IO. In light of that, it seems
preferable to use an implementation that cannot cause a stack
overflow.

A second question that might be asked about this analysis is: "Was it
necessary to introduce the added complexity of `core_bench` to measure
the performance of `map`?" For example, one might set up a performance
test with just successive calls to `Time.now` or
`Unix.gettimeofday`. In an earlier draft of this article, I tried such
an
[approach](https://github.com/jsthomas/ocaml-analysis/blob/master/map/profile.ml),
producing some misleading data. In that test, I did a full garbage
collection in between runs (applications of `map`), which suppressed
that (nontrivial) cost and made the tail recursive implementation
appear quite fast. `core_bench` does a much better job incorporating
the cost of garbage collection by varying the number of test runs
performed in a row and then establishing a trend (with linear
regression) that reflects the amortized cost of garbage collection per
run.

One interesting finding did arise from my earlier tests: for short
lists, allocating memory on the heap actually appears to be faster
than creating frames on the stack. Since the tests perform a full
garbage collection between test runs, the timings show only the cost
of allocating space on the heap. This produced data like the
following:

**Summary Statistics, $N=10^3$ Garbage Collected Map Benchmark Times (μs)**

<table class="dataframe">
  <thead>
    <tr>
      <th></th>
      <th>Std. Lib.</th>
      <th>NTR</th>
      <th>Base</th>
      <th>Batteries</th>
      <th>Containers</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>Mean</th>
      <td>27.18</td>
      <td>27.21</td>
      <td>11.23</td>
      <td>19.03</td>
      <td>13.06</td>
    </tr>
    <tr>
      <th>Min</th>
      <td>15.97</td>
      <td>14.07</td>
      <td>6.91</td>
      <td>9.06</td>
      <td>7.87</td>
    </tr>
    <tr>
      <th>25%</th>
      <td>18.84</td>
      <td>17.88</td>
      <td>7.15</td>
      <td>10.97</td>
      <td>10.01</td>
    </tr>
    <tr>
      <th>50%</th>
      <td>20.03</td>
      <td>19.07</td>
      <td>8.11</td>
      <td>15.50</td>
      <td>10.01</td>
    </tr>
    <tr>
      <th>75%</th>
      <td>23.13</td>
      <td>22.17</td>
      <td>12.87</td>
      <td>18.84</td>
      <td>10.97</td>
    </tr>
    <tr>
      <th>Max</th>
      <td>849.01</td>
      <td>576.02</td>
      <td>379.80</td>
      <td>622.03</td>
      <td>434.88</td>
    </tr>
  </tbody>
</table>

**Summary Statistics, $N=10^4$ Garbage Collected Map Benchmark Times (μs)**
<table class="dataframe">
  <thead>
    <tr>
      <th></th>
      <th>Std. Lib.</th>
      <th>NTR</th>
      <th>Base</th>
      <th>Batteries</th>
      <th>Containers</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>Mean</th>
      <td>230.23</td>
      <td>216.60</td>
      <td>141.39</td>
      <td>144.59</td>
      <td>161.56</td>
    </tr>
    <tr>
      <th>Min</th>
      <td>77.01</td>
      <td>73.91</td>
      <td>61.04</td>
      <td>54.84</td>
      <td>63.18</td>
    </tr>
    <tr>
      <th>25%</th>
      <td>97.04</td>
      <td>86.07</td>
      <td>67.95</td>
      <td>58.89</td>
      <td>70.81</td>
    </tr>
    <tr>
      <th>50%</th>
      <td>121.95</td>
      <td>99.90</td>
      <td>75.10</td>
      <td>61.99</td>
      <td>77.01</td>
    </tr>
    <tr>
      <th>75%</th>
      <td>193.83</td>
      <td>284.91</td>
      <td>148.59</td>
      <td>118.26</td>
      <td>175.24</td>
    </tr>
    <tr>
      <th>Max</th>
      <td>12719.87</td>
      <td>2753.97</td>
      <td>2960.21</td>
      <td>3616.09</td>
      <td>13603.93</td>
    </tr>
  </tbody>
</table>

When we ignore the time spent on garbage collection, we see that `ntr`
is surprisingly competitive, especially in comparison with `stdlib`;
the difference between the two implementations, of course, is that
`ntr` allocates more memory on the heap while `stdlib` creates more
stack frames.

## Notes

Thanks to [Anton Bachin](https://github.com/aantron) and
[Simon Cruanes](https://github.com/c-cube/) for reading drafts of this
post.
