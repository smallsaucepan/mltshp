from lib.utilities import base36decode, base36encode

import tornado.web
from .base import BaseHandler, require_membership
from models import User, Sharedfile, notification


class IncomingHandler(BaseHandler):
    @tornado.web.authenticated
    @require_membership
    def get(self, before_or_after=None, base36_id=None):
        """
        path: /incoming
        """
        current_user_obj = self.get_current_user_object()
        notifications_count = notification.Notification.for_user_count(current_user_obj)

        older_link, newer_link = None, None
        sharedfile_id = None
        if base36_id:
            sharedfile_id = base36decode(base36_id)

        before_id, after_id = None, None
        if sharedfile_id and before_or_after == 'before':
            before_id = sharedfile_id
        elif sharedfile_id and before_or_after == 'after':
            after_id = sharedfile_id

        # We're going to older, so ony use before_id.
        if before_id:
            sharedfiles = Sharedfile.incoming(before_id=before_id,per_page=11)
            # we have nothing on this page, redirect to base incoming page.
            if len(sharedfiles) == 0:
                return self.redirect('/incoming')

            if len(sharedfiles) > 10:
                older_link = "/incoming/before/%s" % sharedfiles[9].share_key
                newer_link = "/incoming/after/%s" % sharedfiles[0].share_key
            else:
                newer_link = "/incoming/after/%s" % sharedfiles[0].share_key

        # We're going to newer
        elif after_id:
            sharedfiles = Sharedfile.incoming(after_id=after_id, per_page=11)
            if len(sharedfiles) <= 10:
                return self.redirect('/incoming')
            else:
                sharedfiles.pop(0)
                older_link = "/incoming/before/%s" % sharedfiles[9].share_key
                newer_link = "/incoming/after/%s" % sharedfiles[0].share_key
        else:
            # clean home page, only has older link
            sharedfiles = Sharedfile.incoming(per_page=11)
            if len(sharedfiles) > 10:
                older_link = "/incoming/before/%s" % sharedfiles[9].share_key

        # Get most popular shared files 1, 2, 5 and 10 years ago. If no files
        # that day, still returns a null (so always 4 results) and we handle
        # the gap gracefully below.
        timehop_tmp = Sharedfile.object_query("""
            WITH target_dates AS (
                SELECT 1 AS years_ago, CURDATE() - INTERVAL 1 YEAR AS target_date
                UNION ALL
                SELECT 2, CURDATE() - INTERVAL 2 YEAR
                UNION ALL
                SELECT 5, CURDATE() - INTERVAL 5 YEAR
                UNION ALL
                SELECT 10, CURDATE() - INTERVAL 10 YEAR
            ),
            ranked_posts AS (
                SELECT
                    t.years_ago,
                    p.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY t.years_ago
                        ORDER BY p.like_count DESC
                    ) AS rn
                FROM target_dates t
                LEFT JOIN sharedfile p
                    ON DATE(p.created_at) = t.target_date
            )
            SELECT *
            FROM ranked_posts
            WHERE rn = 1
            ORDER BY years_ago;
        """)

        # Pass to the view: label, share_key of next shared_file, shared_file
        # We use the share_key of next shared file to link into the incoming
        # feed timeline with our target image at the top of the page.
        timehop_sharedfiles = []
        labels = ["1 year ago", "2 years ago", "5 years ago", "10 years ago"]
        for i, label in enumerate(labels):
            item = timehop_tmp[i] if timehop_tmp[i].id else None
            if (item):
                timehop_sharedfiles.append((label, self.__next_share_key(item), item))
            else:
                # Placeholder
                timehop_sharedfiles.append((label, None, None))

        return self.render("incoming/index.html", sharedfiles=sharedfiles[0:10],
            current_user_obj=current_user_obj,
            older_link=older_link, newer_link=newer_link,
            notifications_count=notifications_count,
            timehop_sharedfiles=timehop_sharedfiles)

    # Return the share key of the next shared file.
    def __next_share_key(self, sharedfile):
        if sharedfile is None:
            return None
        return base36encode(sharedfile.id + 1)
