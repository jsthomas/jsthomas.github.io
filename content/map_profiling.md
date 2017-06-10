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

* The implementation above (which I'll refer to as the control) is not
  *tail recursive*, so it takes space on the stack proportional to the
  length of the input list. For long enough lists, this causes a
  stack overflow.

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

I wrote
[this program](https://github.com/jsthomas/ocaml-analysis/blob/master/map/profile.ml)
to compare performance between the five implementations I described
above. Specifically:

* I tested each algorithm against lists of lengths $N=10^3, 10^4$ and
  $10^5$. On my system, $N=10^5$ was the highest power of 10 for which
  the naive implementation did not fail due to a stack overflow.
* Each list consisted of integer elements (all 0), and the function
  mapped onto the list simply added one to each element.
* I measured each call to map with `Unix.gettimeofday` (which seems to
  have better resolution than `Unix.times`).
* I collected 1000 measurements for each pair of (implementation,
  $N$), using `Gc.full_major` to trigger a garbage collection between
  runs.
* I ran these tests on a Lenovo X220, Intel Core i5-2520M CPU (2.50GHz ×
  4 cores), and 4GB RAM.

# Results

**Median Map Times (μs) versus N**
<table class="dataframe">
  <thead>
    <tr>
      <th>N</th>
      <th>Control</th>
      <th>Tail Recursive</th>
      <th>Containers</th>
      <th>Batteries</th>
      <th>Base</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>1000</th>
      <td>20.03</td>
      <td>19.07</td>
      <td>10.01</td>
      <td>15.50</td>
      <td>8.11</td>
    </tr>
    <tr>
      <th>10000</th>
      <td>121.95</td>
      <td>99.90</td>
      <td>77.01</td>
      <td>61.99</td>
      <td>75.10</td>
    </tr>
    <tr>
      <th>100000</th>
      <td>4835.97</td>
      <td>7393.48</td>
      <td>7177.11</td>
      <td>5104.07</td>
      <td>7130.98</td>
    </tr>
  </tbody>
</table>

The medians alone suggest no single implementation is best overall and
that the control only outperforms the tail recursive version for
fairly large $N$. I would guess that most lists in practice are
shorter than 1000 elements; in that case, `base` appears to be
preferable.

I wanted to get a more detailed look at how the timings were
distributed in each trial. Below are histograms for each
implementation, and some further summary statistics. (Note: In these
histograms the highest bin is open-ended, i.e. $[K, \infty)$):

![Histograms N=1000]({filename}/images/map_profiling/hist10^3.png)

![Histograms N=10000]({filename}/images/map_profiling/hist10^4.png)

![Histograms N=100000]({filename}/images/map_profiling/hist10^5.png)

**Summary Statistics, $N=10^3$ Map Benchmark Times (μs)**

<table class="dataframe">
  <thead>
    <tr>
      <th></th>
      <th>Control</th>
      <th>Tail Rec.</th>
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

**Summary Statistics, $N=10^4$ Map Benchmark Times (μs)**
<table class="dataframe">
  <thead>
    <tr>
      <th></th>
      <th>Control</th>
      <th>Tail Rec.</th>
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

**Summary Statistics, $N=10^5$ Map Benchmark Times (μs)**
<table class="dataframe">
  <thead>
    <tr>
      <th></th>
      <th>Control</th>
      <th>Tail Rec.</th>
      <th>Base</th>
      <th>Batteries</th>
      <th>Containers</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>Mean</th>
      <td>6071.46</td>
      <td>9529.15</td>
      <td>9257.47</td>
      <td>6397.77</td>
      <td>9307.99</td>
    </tr>
    <tr>
      <th>Min</th>
      <td>2696.04</td>
      <td>3623.96</td>
      <td>3582.95</td>
      <td>2647.88</td>
      <td>3551.01</td>
    </tr>
    <tr>
      <th>25%</th>
      <td>3667.29</td>
      <td>6251.45</td>
      <td>6265.58</td>
      <td>3757.12</td>
      <td>6388.78</td>
    </tr>
    <tr>
      <th>50%</th>
      <td>4835.97</td>
      <td>7393.48</td>
      <td>7130.98</td>
      <td>5104.07</td>
      <td>7177.11</td>
    </tr>
    <tr>
      <th>75%</th>
      <td>6349.86</td>
      <td>9692.43</td>
      <td>8736.14</td>
      <td>6772.99</td>
      <td>8820.65</td>
    </tr>
    <tr>
      <th>Max</th>
      <td>38676.98</td>
      <td>28940.92</td>
      <td>59360.03</td>
      <td>24572.13</td>
      <td>27489.90</td>
    </tr>
  </tbody>
</table>

Several further things I notice:

* For $N=10^3$, `base` is consistently fastest at all percentiles.

* `base`, `batteries`, and `containers` consistently outperform the
  control and tail-recursive implementations.

* In the $N=10^5$ case, the distribution of times is oddly bimodal
  across all implementations. Possibly this points to a weakness in my
  experimental setup.

# Conclusions

For very large $N$, there does appear to be a penalty to using a naive
tail recursive implementation of `map`; in that case, assuming one
looks at just the median or mean, the control implementation completes
the same work in about 63-65% of the time. Given the choice, one
should probably prefer one of the optimized implementations in more
recent libraries.

There is an argument
([here, for example](http://caml.inria.fr/pub/ml-archives/caml-list/1999/01/bcabe938d378046308a1901cfef6ef67.fr.html))
that the non-tail recursive (control) implementation should be
preferred to the tail recursive version. The tail recursive version is
just too slow for small and medium sized lists, the argument goes, due
to the additional time to allocate memory. The data here disagrees
with that argument; in fact the tail recursive version is only slower
for lists whose length approaches the point of causing a stack
overflow in the non-tail recursive implementation.

A follow up question to this analysis, especially in the context of
the discussion of the implementation of `Lwt.map` is: "How significant
is the cost of `map` compared to other operations?" To partially
address this, I wrote
[another program](https://github.com/jsthomas/ocaml-analysis/blob/master/map/buff_test.ml)
that measures how long it takes to write $M$ bytes to a Unix pipe
using `Lwt.write`. Measuring 1000 trials of writing 4096 bytes to a
pipe, I obtained the following table.

**Summary Statistics, Unix Pipe Write Benchmark Times (μs)**
<table class="dataframe">
  <thead>
    <tr>
      <th>Mean</th>
      <th>Min</th>
      <th>25%</th>
      <th>50%</th>
      <th>75%</th>
      <th>Max</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>2.80</td>
      <td>0.95</td>
      <td>1.91</td>
      <td>2.15</td>
      <td>3.10</td>
      <td>30.04</td>
    </tr>
  </tbody>
</table>

There appear to be some significant outliers in this experiment as
well, but overall we can see that the distribution is pretty tightly
grouped around 2-4 μs.

It seems reasonable to estimate that `Lwt.map` would primarily be
applied to IO operations like the ones in this experiment. With that
premise, the data suggests the cost of using the slowest
implementation of map to write 4096 bytes to each of 1000 unix pipes
would be about 0.9% of the total time required to complete the
operation, at the median (20.03 μs to map, 2150 μs to write all the
data). Overall, I take this to mean that the implementation of `map`
shouldn't be a significant concern; the real cost is performing IO. In
light of that, it seems preferable to use an implementation that
can't produce a stack overflow.
