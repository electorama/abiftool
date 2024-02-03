# abiftool.py
*ABIF conversion utility*

A script (abiftool.py) which converts between [ABIF](https://electowiki.org/wiki/ABIF) and other commonly-used electoral expression formats.

**Homepage**: [https://electorama.com/abiftool](https://electorama.com/abiftool)

## Getting started
To try `abiftool.py`, perform the following steps:

1. Drop to a shell prompt, and change to a directory for a local copy of `abiftool.py` and supporting tests and libraries.
2. Clone the repo:
```
git clone https://github.com/electorama/abiftool.git
cd abiftool
```
3. Run an example command (see below)

## Examples
### Burlington 2009
The following command runs with test data checked into this repository:
```
./abiftool.py -t texttable testdata/burl2009/burl2009.abif
```

The expected output is a table with the pairwise output from the election described in ```burl2009.abif```:

```
+------------------+----------+------+--------+-------+---------+----------+
+    Loser ->      + Montroll | Kiss | Wright | Smith | Simpson | Write-in |
+ v Winner         +          |      |        |       |         |          |
+==================+==========+======+========+=======+=========+==========+
+ Montroll (5-0-0) + None     | 4067 | 4597   | 4573  | 6267    | 6658     |
+------------------+----------+------+--------+-------+---------+----------+
+ Kiss (4-1-0)     + 3477     | None | 4314   | 3946  | 5517    | 6149     |
+------------------+----------+------+--------+-------+---------+----------+
+ Wright (3-2-0)   + 3668     | 4064 | None   | 3975  | 5274    | 6063     |
+------------------+----------+------+--------+-------+---------+----------+
+ Smith (2-3-0)    + 2998     | 3577 | 3793   | None  | 5573    | 6057     |
+------------------+----------+------+--------+-------+---------+----------+
+ Simpson (1-4-0)  + 591      | 845  | 1309   | 721   | None    | 3338     |
+------------------+----------+------+--------+-------+---------+----------+
+ Write-in (0-5-0) + 104      | 116  | 163    | 117   | 165     | None     |
+------------------+----------+------+--------+-------+---------+----------+
```

The table above expresses the same results that can be found in the "Pairwise results" table in the article:

[https://electowiki.org/wiki/2009_Burlington_mayoral_election#Pairwise_results](https://electowiki.org/wiki/2009_Burlington_mayoral_election#Pairwise_results)

## Licensing
abiftool.py is currently licensed under the GNU General Public License version 3 (GPLv3).  As of this writing (in February 2024), the primary author can probably be convinced to switch to an MIT, BSD, or Apache license of some sort. Visit [electorama/abiftool#1](https://github.com/electorama/abiftool/issues/1) to discuss this topic.

## More info...
More about the formats supported, history of the project, and future plans for abiftool can be found on the homepage for this project:
[https://electorama.com/abiftool](https://electorama.com/abiftool)
