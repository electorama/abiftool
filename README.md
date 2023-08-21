# abiftool.py
Conversion of ABIF to/from other formats

As of this writing in August 2023, this script (abiftool.py) aspires to convert between ABIF and other commonly-used electoral expression formats.  As of right now, conversion is limited to the following formats:

* ABIF (or ".abif") - The _Aggregated Ballot Information Format_ provides a concise, aggregated, text-based document to describe the ballots cast in range-based or ranked elections, as well as approval-based and choose-one balloting systems. See https://github.com/electorama/abif for more.
* .jabmod - this is a JSON model for ABIF.  It's quite likely that many future conversions to/from .abif using abiftool will use .jabmod as an interim/internal format
* .widj - this is the JSON representation used by Electowidget, a format

The primary author of abiftool.py (Rob Lanphier, a.k.a. "robla") has not yet fully decided on the following:
* What the long-term license will be (it's currently licensed under GPLv3), but as of this writing (in August 2023), the primary author can probably be convinced to switch to an MIT, BSD, or Apache license of some sort.  As other contributors contribute under GPLv3, it will become more difficult for the primary author to convince other contributors to change license.  Visit [electorama/abiftool#1](https://github.com/electorama/abiftool/issues/1) to discuss this topic.
* What formats/tools the primary author should focus on interoperability with.  There are many tools and formats out there.  Where to start?  Visit https://github.com/electorama/abif/issues/29 to discuss this topic.

Please file issues in [the abiftool.py issue tracker](https://github.com/electorama/abiftool/issues) if you notice problems with the tool that likely need to get fixed sooner rather than later.  Please participate in the broader ABIF project (at https://github.com/electorama/abif ) to help define the ABIF format.
