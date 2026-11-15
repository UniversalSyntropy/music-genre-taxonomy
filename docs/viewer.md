# Viewer guide

The viewer is a web page that draws the genre tree. Open it at [universalsyntropy.github.io/music-genre-taxonomy](https://universalsyntropy.github.io/music-genre-taxonomy/).

## Controls

| Action | Result |
| --- | --- |
| Drag | Move the tree |
| Scroll or pinch | Zoom |
| Click a name | Open or close its branch and show its detail card |
| Type in the search box | Find a genre, open the path to it and zoom to it |
| Theme menu | Change the colour theme (light or dark) |
| View menu | Change between the tree and the point cloud. The point cloud shows each genre as one dot. A circle holds a genre and its sub-genres, and each large circle is one top genre. Names appear as you zoom in. Click a dot to show its detail card. Add `view=cloud` to the address to open it at the start |
| Show root genres box | Point cloud only. The top genres show as circle names. Tick the box to show their own dots too |
| Breadcrumb bar | Shows the drawn path from "All genres" to the selected genre. Click a step to go to it |
| Fit | Fit the whole tree in the window |
| Open one more level | Open the next level of branches |
| Close all | Close every branch |

## Reading the tree

- **Filled dot:** a tag-level genre. It is a good value for a file's genre tag.
- **Hollow dot:** a genre that is not tag level. It is broader or narrower than a usual file tag.
- **One place per genre:** the tree shows each genre once, under its nearest parent. The detail card lists every parent.

## Detail card

The card shows the name, the parents and the ids. Its links open in a new tab:

- Wikipedia
- Wikidata
- MusicBrainz
- Discogs
- Beatport search

The Beatport link is a search for the genre name. The viewer does not know if Beatport uses that name.

## Themes

| Menu entry | Result |
| --- | --- |
| Theme: Match my device | Light or dark, as your device is set |
| Light theme: Chalk (warm) | Warm off-white |
| Light theme: Frost (cool blue) | Pale blue |
| Dark theme: Slate (grey) | Dark grey |
| Dark theme: Dusk (navy) | Dark navy |

The viewer remembers your choice in the local storage of your browser.

## Deep links and genre pages

- **Deep link:** add `?g=<key>` to the viewer address. The viewer opens that genre. Example: `?g=acid-house`.
- **Genre page:** each genre has one static page at `genre/<key>.html`. These pages give search engines one address per genre.

## Privacy

- The viewer sets no cookie.
- The viewer has no tracker.
- The viewer makes no request to another site. The d3 library is in the repo (`site/vendor/`).
- Links on the detail card go to other sites only when you click them.

## Build the site

Run `python tools/build_site.py` after `python tools/build.py` and `python tools/check.py`. The [data guide](data-guide.md) describes the data that the viewer reads.
