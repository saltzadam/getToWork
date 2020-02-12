# getToWork
Commute calendar on Boston MBTA

Want to know how long your Boston public transit commute will be? You can use Google Maps (et al.), but it only shows you a range of possible times. getToWork will tell you how long that commute took on a particular day. It uses the MBTA's realtime tracking data.

Currently will take two stop names (approximate names are OK) and a start time.  It will return up to 5 (epoch) times when you would arrive. It's a small step to pick the closest time and to tell the user which route it came from. I think some of the issues below deserve some attention before improving the UI or anything else.

Some ongoing issues:

- The routes come through the Google Maps API.
  - Google maps does not (publicly) connect MBTA stop names with official MBTA stop_ids.  Most stop names correspond to multiple stop_ids.  For example, "Harvard Square" consists of two Red Line stops (inbound and outbound) as well as bus stops.  The program uses MBTA trip data to infer which stop is meant.  Unfortunately this is quite slow.

Much of this work could be done ahead of time, e.g. by creating lists of stops which are directly accessible from each other.  

  - Some of the routes include non-MBTA transit, e.g. the Peter Pan bus or university shuttles.  It would be cool to handle the shuttles but I can't right now, so those routes just return a time of zero.  
- MBTA reliability data for buses is somewhat limited, so bus-based routes may not work.
- Reliability data for terminal stations -- the ends of the lines -- are limited. Many terminal stations are very close to a non-terminal station, e.g. Boston College and South Street on the B-line.  So I've shifted all routes through Boston College to instead start/stop at South St.  This should be done for the remaining routes and a warning should be added.
