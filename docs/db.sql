create table if not exists reference_doc
(
    reference_id bigint unsigned auto_increment
        primary key,
    document     text                                not null,
    created_at   timestamp default CURRENT_TIMESTAMP not null
)
    charset = utf8mb4;

create table if not exists user
(
    user_id           bigint unsigned auto_increment
        primary key,
    email             varchar(255)                        not null,
    name              varchar(100)                        not null,
    profile_image_url varchar(512)                        null,
    auth_provider     varchar(50)                         not null,
    provider_user_id  varchar(255)                        null,
    job_role          varchar(100)                        null,
    team_name         varchar(100)                        null,
    created_at        timestamp default CURRENT_TIMESTAMP not null,
    updated_at        timestamp default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP,
    constraint uk_user_email
        unique (email)
)
    charset = utf8mb4;

create table if not exists github_issue
(
    github_issue_id     bigint unsigned auto_increment
        primary key,
    user_id             bigint unsigned                     not null,
    repo_owner          varchar(100)                        not null,
    repo_name           varchar(200)                        not null,
    issue_number        int                                 not null,
    title               varchar(255)                        not null,
    body                text                                null,
    state               varchar(30)                         null,
    external_created_at timestamp                           null,
    external_updated_at timestamp                           null,
    closed_at           timestamp                           null,
    created_at          timestamp default CURRENT_TIMESTAMP not null,
    updated_at          timestamp default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP,
    constraint uk_github_issue_repo_number
        unique (repo_owner, repo_name, issue_number),
    constraint fk_github_issue_user
        foreign key (user_id) references user (user_id)
)
    charset = utf8mb4;

create table if not exists integration
(
    integration_id   bigint unsigned auto_increment
        primary key,
    user_id          bigint unsigned                      not null,
    provider         varchar(50)                          not null,
    access_token     text                                 null,
    refresh_token    text                                 null,
    token_expires_at timestamp                            null,
    is_active        tinyint(1) default 1                 not null,
    created_at       timestamp  default CURRENT_TIMESTAMP not null,
    updated_at       timestamp  default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP,
    constraint fk_integration_user
        foreign key (user_id) references user (user_id)
)
    charset = utf8mb4;

create table if not exists notification
(
    notification_id bigint unsigned auto_increment
        primary key,
    user_id         bigint unsigned                     not null,
    push_token      varchar(512)                        null,
    on_off          tinyint(1)                          not null,
    created_at      timestamp default CURRENT_TIMESTAMP not null,
    constraint fk_notification_user
        foreign key (user_id) references user (user_id)
)
    charset = utf8mb4;

create table if not exists project
(
    project_id    bigint unsigned auto_increment
        primary key,
    user_id       bigint unsigned                     not null,
    creation_type varchar(50)                         not null,
    project_name  varchar(200)                        not null,
    created_at    timestamp default CURRENT_TIMESTAMP not null,
    updated_at    timestamp default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP,
    constraint fk_project_user
        foreign key (user_id) references user (user_id)
)
    charset = utf8mb4;

create table if not exists slack_message
(
    slack_message_id bigint unsigned auto_increment
        primary key,
    user_id          bigint unsigned                     not null,
    message_ts       timestamp                           not null,
    sender_name      varchar(100)                        null,
    text             text                                not null,
    created_at       timestamp default CURRENT_TIMESTAMP not null,
    constraint fk_slack_message_user
        foreign key (user_id) references user (user_id)
)
    charset = utf8mb4;

create index idx_slack_message_user_date
    on slack_message (user_id, message_ts);

create table if not exists subject
(
    subject_id           bigint unsigned auto_increment
        primary key,
    user_id              bigint unsigned                     not null,
    creation_type        varchar(50)                         not null,
    creation_type_detail varchar(100)                        null,
    my_role              text                                null,
    situation            text                                null,
    created_at           timestamp default CURRENT_TIMESTAMP not null,
    updated_at           timestamp default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP,
    conversation_date    date                                null,
    message_count        int                                 null,
    constraint fk_subject_user
        foreign key (user_id) references user (user_id)
)
    charset = utf8mb4;

create table if not exists scenario
(
    scenario_id bigint unsigned auto_increment
        primary key,
    subject_id  bigint unsigned                                       not null,
    user_id     bigint unsigned                                       not null,
    title       varchar(200)                                          not null,
    ai_role     varchar(100)                                          null,
    topic_type  enum ('overview', 'detail') default 'detail'          not null,
    status      varchar(50)                 default 'draft'           not null,
    created_at  timestamp                   default CURRENT_TIMESTAMP not null,
    updated_at  timestamp                   default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP,
    constraint fk_scenario_subject
        foreign key (subject_id) references subject (subject_id),
    constraint fk_scenario_user
        foreign key (user_id) references user (user_id)
)
    charset = utf8mb4;

create table if not exists scenario_reference
(
    scenario_id  bigint unsigned                     not null,
    reference_id bigint unsigned                     not null,
    created_at   timestamp default CURRENT_TIMESTAMP not null,
    primary key (scenario_id, reference_id),
    constraint fk_scenario_reference_reference
        foreign key (reference_id) references reference_doc (reference_id),
    constraint fk_scenario_reference_scenario
        foreign key (scenario_id) references scenario (scenario_id)
)
    charset = utf8mb4;

create table if not exists scenario_session
(
    session_id          bigint unsigned auto_increment
        primary key,
    scenario_id         bigint unsigned                      not null,
    user_id             bigint unsigned                      not null,
    status              varchar(30)                          not null,
    total_turns_planned int                                  not null,
    played_turns        int        default 0                 not null,
    completed_all_turns tinyint(1) default 0                 not null,
    finish_reason       varchar(50)                          null,
    created_at          timestamp  default CURRENT_TIMESTAMP not null,
    updated_at          timestamp  default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP,
    finished_at         timestamp                            null,
    constraint fk_scenario_session_scenario
        foreign key (scenario_id) references scenario (scenario_id),
    constraint fk_scenario_session_user
        foreign key (user_id) references user (user_id)
)
    charset = utf8mb4;

create table if not exists scenario_feedback
(
    feedback_id         bigint unsigned auto_increment
        primary key,
    session_id          bigint unsigned                     not null,
    scenario_id         bigint unsigned                     not null,
    total_pronunciation decimal(5, 2)                       null,
    total_grammar       decimal(5, 2)                       null,
    total_diversity     decimal(5, 2)                       null,
    total_score         decimal(5, 2)                       null,
    comment             text                                null,
    created_at          timestamp default CURRENT_TIMESTAMP not null,
    constraint fk_scenario_feedback_scenario
        foreign key (scenario_id) references scenario (scenario_id),
    constraint fk_scenario_feedback_session
        foreign key (session_id) references scenario_session (session_id)
)
    charset = utf8mb4;

create table if not exists scenario_message
(
    message_id   bigint unsigned auto_increment
        primary key,
    session_id   bigint unsigned                     not null,
    turn_index   int                                 not null,
    speaker      varchar(30)                         not null,
    message_text text                                not null,
    audio_url    text                                null,
    created_at   timestamp default CURRENT_TIMESTAMP not null,
    constraint fk_scenario_message_session
        foreign key (session_id) references scenario_session (session_id)
)
    charset = utf8mb4;

create index idx_scenario_message_session_turn
    on scenario_message (session_id, turn_index);

create table if not exists scenario_message_feedback
(
    feedback_id          bigint unsigned auto_increment
        primary key,
    message_id           bigint unsigned                     not null,
    session_id           bigint unsigned                     not null,
    original_expression  text                                null,
    suggested_expression text                                null,
    pronunciation        decimal(5, 2)                       null,
    grammar              decimal(5, 2)                       null,
    diversity            decimal(5, 2)                       null,
    score                decimal(5, 2)                       null,
    criterion            varchar(50)                         null,
    created_at           timestamp default CURRENT_TIMESTAMP not null,
    constraint fk_scenario_message_feedback_message
        foreign key (message_id) references scenario_message (message_id),
    constraint fk_scenario_message_feedback_session
        foreign key (session_id) references scenario_session (session_id)
)
    charset = utf8mb4;

