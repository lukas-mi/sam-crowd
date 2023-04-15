CREATE TABLE hit_configs (
    hitid VARCHAR(128) PRIMARY KEY,
    annotation_mode VARCHAR(128) NOT NULL,
    publisher VARCHAR(20) NOT NULL,
    article VARCHAR(128) NOT NULL,
    excerpt VARCHAR(128) NOT NULL,
    lang VARCHAR(20) NOT NULL,
    created TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
)
