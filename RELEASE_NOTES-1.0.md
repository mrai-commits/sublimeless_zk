# Sublimeless Zettelkasten 1.0

The first release since 0.9. It brings the app to current versions of Python and Qt, fixes the bugs below, and adds new functions, which are described in the README under [New in version 1.0](README.md#new-in-version-10).

## Bug fixes

**Crashes and hangs**

* <kbd>alt</kbd> + click on a link to a note that does not exist no longer crashes the app. It lists the notes that contain the link.
* Replace all no longer hangs when the replacement contains the search text (e.g. replacing `A` by `A B`).
* `.bib` entries that have an editor but no author no longer crash the citation list.
* An unexpected error in any command no longer closes the whole app. A message appears in the status bar, the details go to a log file, and you can keep working.
* The app no longer refuses to start when MultiMarkdown is not available; the HTML export then uses the basic parser.

**Editing and highlighting**

* Numbered lists: the wrong characters of a line were coloured. Lists on the second and deeper levels are highlighted.
* Citations without author or with a prefix, `[-@key]` and `[e.g., @key]`, are highlighted and clickable.
* Two or more web links on one line: each one is highlighted and clickable, instead of the rest of the line being swallowed.
* Long web links that wrap over several lines are clickable.
* A citation or link in a heading no longer breaks its entry in the table of contents.
* The text of a numbered list item has the normal text color; only the number is colored.
* A tag at the start of a line (`#idea`) is a tag and no longer shown as a heading. As in standard Markdown, a heading needs a space after the `#`.
* Typing in long notes is fast again. A note of 9,400 words needed 580 ms per keystroke; now about 40 ms.

**Shortcuts**

* Shortcuts with <kbd>shift</kbd> or <kbd>alt</kbd> that the editor uses for something else now reach the app's command. Before, the editor kept them: <kbd>ctrl/cmd</kbd> + <kbd>shift</kbd> + <kbd>L</kbd>, for example, deleted the line.

**Find and replace**

* Replace changes the highlighted match, not the one after it.
* The case-sensitive and whole-word options are used as set at the time of the search.
* <kbd>tab</kbd> moves from the find field to the replace field instead of inserting a tab.

**Notes and files**

* After renaming a note, the old name no longer stays in the list of open notes.
* Renaming never overwrites an existing note.
* Note titles are no longer cut at the first period (e.g. "Ch. 5").

**Bibliographies**

* The automatic bibliography finds citations separated by a semicolon: `[@a; @b]`.
* The automatic bibliography works with pandoc 2.11 and later, which no longer has the `pandoc-citeproc` filter.
* The citation list shows editors and year for `.bib` entries that take them from a parent entry via `crossref`.

**Other**

* On Linux, web links are opened without passing the address through a shell.

## Changed shortcuts

* Insert bibliography moved from <kbd>ctrl/cmd</kbd> + <kbd>B</kbd> to <kbd>ctrl/cmd</kbd> + <kbd>alt/opt</kbd> + <kbd>B</kbd>. <kbd>ctrl/cmd</kbd> + <kbd>B</kbd> now makes text bold.
* Citations open with <kbd>ctrl/cmd</kbd> + click. A plain click places the cursor. `"citations_need_cmd_click": false` restores the old behaviour.
