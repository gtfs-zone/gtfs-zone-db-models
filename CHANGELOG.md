## v0.2.0 (2026-10-01)

### BREAKING CHANGE

- consumers import gtfs_zone_db_models and run gtfs-zone-db-models-migrate

### Feat

- rename the package to gtfs-zone-db-models
- **keys**: add vehicle_keys, the one definition of the live keyspace
- **store**: an S3 object store seam, and the hosted-feed model
- **events**: the per-feed pub/sub channel and its load payload
- **tracker**: surrogate primary key, rule dates, and rule exceptions
- **identity**: record the broker and when a credential was last used
- add FeedInvite for sharing with users who have not signed in
- add FeedMember so feeds can be shared
- split User into a person and its Identities
- remove TripAlias model and drop its table
- retire Driver, add Tracker (secret id + public nickname)
- add DriverRule model and trip resolver
- initial commit

### Fix

- **tracker**: enforce the colon-free id rule where ids are born
- **store**: ignore unrelated .env keys in ObjectStoreSettings
- **resolver**: keep the tracker when no rule matches
- **alembic**: give the description_text-widening revision a unique id
- **service-alert**: widen description_text to unbounded text
- **alembic**: give the broker_alias revision a unique id

### Refactor

- move alemic into src
