This module hides the **Delete** entry from the Action (cog) menu of list and
form views, without touching the underlying delete (unlink) permission.

Visibility is controlled per user through the **Show Delete Action** security
group:

* Users **not** in the group do not see the Delete entry (default).
* Users **in** the group keep the Delete entry as usual.

The administrator is added to the group on installation, so the installer is
not locked out. Assign the group to any other user (Settings > Users, Extra
Rights) to let them delete records from the Action menu.
