High priority
=============

- We want persistent composers where one can choose the CSS that's
  used for sending out the message. (nouri)

- Add proper logging support. (nouri)

Medium priority
===============

- A plain text composer plus template.

- The collector needs to be clever about caching results.

- We need to test the queue and see after how many messages it makes
  sense to commit back.  The relevant code is in
  ``collective.singing.message``.

- Make an ISubscription that holds reference to the member id.  This
  would allow us to implement collectors that filter based on
  subscribers' permissions.

- Make the subscription form (``my-subscriptions.html``) more
  configurable, e.g. to group subscriptions.
