"""
tasks.py — writing-task prompts for the PROTOTYPE, copied here so the prototype is
fully decoupled from the Stage-1 data-collection app (it never imports it).

Two difficulty levels, each with a pool of variations (a variation is picked so a
returning participant is not shown the exact same prompt every time).
"""

LEVELS = [
    {
        "id": "easy",
        "title": "Everyday writing",
        "difficulty": "Easy",
        "blurb": "A short, familiar topic about your own life — nothing to research.",
        "variations": [
            {"id": "easy_routine",
             "prompt": "Describe your typical morning routine, from waking up to "
                       "starting your day. About 120–180 words."},
            {"id": "easy_food",
             "prompt": "Describe your favourite food or meal. What is it, and why "
                       "do you love it? About 120–180 words."},
            {"id": "easy_place",
             "prompt": "Describe your favourite place to relax. Where is it, and "
                       "how does it make you feel? About 120–180 words."},
            {"id": "easy_weekend",
             "prompt": "Describe how you like to spend an ideal weekend. "
                       "About 120–180 words."},
            {"id": "easy_hobby",
             "prompt": "Describe a hobby or activity you enjoy and explain what "
                       "you like about it. About 120–180 words."},
            {"id": "easy_person",
             "prompt": "Describe a person you admire and explain why they matter "
                       "to you. About 120–180 words."},
        ],
    },
    {
        "id": "moderate",
        "title": "Describe & explain",
        "difficulty": "Moderate",
        "blurb": "A topic that needs a bit of structure, reflection or reasoning.",
        "variations": [
            {"id": "mod_journey",
             "prompt": "Describe a memorable journey or trip you have taken. Where "
                       "did you go, what happened, and what made it stand out? "
                       "About 150–200 words."},
            {"id": "mod_technology",
             "prompt": "Explain how a piece of technology has changed the way you "
                       "live, study or work. Give specific examples. "
                       "About 150–200 words."},
            {"id": "mod_challenge",
             "prompt": "Describe a challenge you faced and explain how you dealt "
                       "with it and what you learned. About 150–200 words."},
            {"id": "mod_compare",
             "prompt": "Compare two things you know well — two cities, two seasons, "
                       "or two hobbies — and explain which you prefer and why. "
                       "About 150–200 words."},
            {"id": "mod_career",
             "prompt": "Describe what your ideal job or career would look like and "
                       "explain why it appeals to you. About 150–200 words."},
            {"id": "mod_tradition",
             "prompt": "Explain a tradition, festival or custom that is important "
                       "in your family or culture, and why it matters to you. "
                       "About 150–200 words."},
        ],
    },
]

TASKS_BY_ID = {}
for _lvl in LEVELS:
    for _v in _lvl["variations"]:
        TASKS_BY_ID[_v["id"]] = {
            "prompt": _v["prompt"],
            "level_id": _lvl["id"],
            "level_title": _lvl["title"],
            "difficulty": _lvl["difficulty"],
        }


def first_variation(level_id):
    """Return the first variation id for a level (simple, deterministic pick)."""
    for lvl in LEVELS:
        if lvl["id"] == level_id:
            return lvl["variations"][0]["id"]
    return None
