"""Opening the first scene, when two requests ask for it at once.

A real database and real concurrency, because that is the only place this
bug exists: every part of it is correct on its own, and what is wrong is what
happens when two of them run at the same time. A stub would agree with the
code and prove nothing.
"""

import asyncio
import unittest
import uuid
from contextlib import asynccontextmanager
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from gary_api import scenes
from gary_api.db import engine
from gary_api.models import Campaign, User


class OpeningTheFirstScene(unittest.TestCase):
    """What prompted this, from a real CI run on main.

    `POST /turns` and `GET /scenes` both ask for the current scene, and the
    campaign page asks for both at once. On a campaign with no scene yet they
    both read nothing, both compute number 1, and both insert — so one of them
    lost to `uq_scenes_campaign_number` and took an unhandled 500 with it. In
    the browser that was a turn that never happened and a page that sat there;
    the e2e tier caught it as a step timing out fifteen seconds later, which
    says nothing at all about the cause.

    Four at once rather than two, because one collision is a coincidence and
    three is the shape of the thing.
    """

    def test_four_at_once_all_get_the_same_scene(self):
        factory = async_sessionmaker(engine, expire_on_commit=False)

        async def campaign_id() -> uuid.UUID:
            async with factory() as database:
                user = User(
                    email=f"{uuid.uuid4()}@example.com", display_name="Race"
                )
                database.add(user)
                await database.flush()
                campaign = Campaign(
                    user_id=user.id,
                    name="Racing",
                    system_slug="dnd-5e",
                    module_slug="the-drowned-belfry",
                )
                database.add(campaign)
                await database.commit()
                return campaign.id

        async def ask(wanted: uuid.UUID) -> int:
            async with factory() as database:
                scene = await scenes.current(database, wanted)
                await database.commit()
                return scene.number

        async def race() -> list:
            wanted = await campaign_id()
            return await asyncio.gather(
                *(ask(wanted) for _ in range(4)), return_exceptions=True
            )

        got = asyncio.run(race())

        raised = [one for one in got if isinstance(one, BaseException)]
        self.assertEqual(raised, [], "asking twice at once raised")
        # All four, and all the same one: losing the race means reading what
        # the winner opened, not opening a second scene beside it.
        self.assertEqual(got, [1, 1, 1, 1])


class AnIntegrityErrorThatIsNotTheRace(unittest.TestCase):
    """Losing the race is read; anything else is still an error.

    The tolerance above is narrow on purpose. It means "somebody else opened
    the scene I was going to open", and the way it knows that is that the
    scene is now there. When it is not there, whatever failed was not this
    race, and swallowing it would turn a real fault into a campaign that
    silently has no scene.

    No database here, deliberately: what this pins is the branch taken when
    the re-read comes back empty, and a real session would only make that
    harder to arrange — as well as fighting the other test in this file over
    a connection pool bound to a different event loop.
    """

    class Session:
        """Just enough session to fail an insert and find nothing after it."""

        async def scalar(self, *_args, **_kwargs):
            return None

        def begin_nested(self):
            @asynccontextmanager
            async def nothing():
                yield None

            return nothing()

    def test_is_raised_rather_than_swallowed(self):
        blew_up = IntegrityError("INSERT", {}, Exception("something else"))

        async def attempt():
            with patch.object(scenes, "_open", side_effect=blew_up):
                await scenes.current(self.Session(), uuid.uuid4())

        with self.assertRaises(IntegrityError):
            asyncio.run(attempt())


if __name__ == "__main__":
    unittest.main()
