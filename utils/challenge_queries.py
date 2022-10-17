CHALLENGE_LIST_QUERY = """
SELECT DISTINCT 
  "challenges"."id", 
  "challenges"."name", 
  "challenges"."photo", 
  "challenges"."updated_at", 
  "challenges"."states", 
  "challenges"."creator_id", 
  "challenges"."parameters", 
  "challenges"."winners_count",
  (select count(*) from challenge_reports 
     where challenge_reports.challenge_id = challenges.id 
       and "state" IN ('A', 'W')
  ) AS "approved_reports_amount", 
  (select string_agg( f, ', ') from (
    select 1 c, 'Вы создатель челленджа' f from challenges c 
      where c.id = challenges.id 
        and c.creator_id = %s and c.organized_by_id <> %s
    union
    select 2, 'Вы организатор челленджа' from challenges c 
      where c.id = challenges.id 
        and c.organized_by_id = %s
    union
    select 2, 'Вы организатор челленджа' from challenge_participants c 
      where c.challenge_id = challenges.id 
        and c.user_participant_id = %s 
        and 'O' = any( c.mode)
    union
    select 4, 'Можно отправить отчёт' from challenges c 
      where c.id = challenges.id 
        and 'C' != all( c.states) 
        --and c.organized_by_id <> %s -- для prod включить!
        and not exists (
            select 1 from challenge_reports c1
              join challenge_participants c2 on c2.id = c1.participant_id
              where c1.challenge_id = challenges.id 
                and c2.user_participant_id = %s) -- проверка на то, что отчет уже отправлялся. если челлендж допускает несколько отчетов, то надо отключить
    union
    select 3, 
      CASE 
        WHEN c.state IN ('S', 'F', 'R') THEN 'Отчёт отправлен' 
        WHEN c.state IN ('A') THEN 'Отчёт подтверждён' 
        WHEN c.state IN ('D') THEN 'Отчёт отклонён' 
        WHEN c.state IN ('W') THEN 'Получено вознаграждение' 
      END
    from challenge_reports c
      where c.challenge_id = challenges.id and c.participant_id in 
        (select id from challenge_participants c1 where c1.challenge_id = challenges.id and c1.user_participant_id = %s)
    order by c
    ) a 
  ) AS "status", 
  (challenges.organized_by_id = %s -- проверка на организатора
     and exists (
       SELECT 1 from challenge_reports c 
         where c.challenge_id = challenges.id AND c."state" IN ('S', 'F', 'R'))) AS "is_new_reports", 
  challenges.start_balance AS "fund" 
FROM challenges
ORDER BY 1 DESC
"""

CHALLENGE_PK_QUERY = """
SELECT 
  "challenges"."id", 
  "challenges"."name", 
  "challenges"."photo", 
  "challenges"."updated_at", 
  "challenges"."states", 
  "challenges"."creator_id", 
  "challenges"."parameters", 
  "challenges"."winners_count",
  "challenges"."end_at",
  "challenges"."description",
  "p"."first_name" AS "first_name",
  "p"."surname" AS "surname",
  "p"."organization_id" AS "organization_pk",
  "p"."photo" AS "profile_photo",
  "p"."tg_name" AS "tg_name",
  (select count(*) from challenge_reports 
     where challenge_reports.challenge_id = challenges.id 
       and "state" IN ('A', 'W')
  ) AS "approved_reports_amount", 
  (select string_agg( f, ', ') from (
    select 1 c, 'Вы создатель челленджа' f from challenges c 
      where c.id = challenges.id 
        and c.creator_id = %s and c.organized_by_id <> %s
    union
    select 2, 'Вы организатор челленджа' from challenges c 
      where c.id = challenges.id 
        and c.organized_by_id = %s
    union
    select 2, 'Вы организатор челленджа' from challenge_participants c 
      where c.challenge_id = challenges.id 
        and c.user_participant_id = %s 
        and 'O' = any( c.mode)
    union
    select 4, 'Можно отправить отчёт' from challenges c 
      where c.id = challenges.id 
        and 'C' != all( c.states) 
        --and c.organized_by_id <> %s -- для prod включить!
        and not exists (
            select 1 from challenge_reports c1
              join challenge_participants c2 on c2.id = c1.participant_id
              where c1.challenge_id = challenges.id 
                and c2.user_participant_id = %s) -- проверка на то, что отчет уже отправлялся. если челлендж допускает несколько отчетов, то надо отключить
    union
    select 3, 
      CASE 
        WHEN c.state IN ('S', 'F', 'R') THEN 'Отчёт отправлен' 
        WHEN c.state IN ('A') THEN 'Отчёт подтверждён' 
        WHEN c.state IN ('D') THEN 'Отчёт отклонён' 
        WHEN c.state IN ('W') THEN 'Получено вознаграждение' 
      END
    from challenge_reports c
      where c.challenge_id = challenges.id and c.participant_id in 
        (select id from challenge_participants c1 where c1.challenge_id = challenges.id and c1.user_participant_id = %s)
    order by c
    ) a 
  ) AS "status", 
  (challenges.organized_by_id = %s -- проверка на организатора
     and exists (
       SELECT 1 from challenge_reports c 
         where c.challenge_id = challenges.id AND c."state" IN ('S', 'F', 'R'))) AS "is_new_reports", 
  challenges.start_balance AS "fund" 
FROM challenges
JOIN auth_user au ON (challenges.creator_id = au.id)
JOIN profiles p ON (p.user_id = challenges.creator_id)
WHERE "challenges"."id" = %s
"""
