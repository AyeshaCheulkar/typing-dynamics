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

# Emotion-writing task (current participant flow): the participant chooses to
# write about a HAPPY or a SAD personal moment. `difficulty` carries the emotion
# label so existing pages (which show a pill) keep working.
MOMENTS = [
    {
        "id": "happy",
        "title": "A happy moment",
        "difficulty": "Happy",
        "blurb": "A moment that made you genuinely happy. Any moment, any size.",
        "free_prompt": "Write about any happy moment. Let it come to you in its own way; there is no right or wrong.",
        "ready_title": "Now, a happy moment",
        "ready_text": "Take a breath and let one come to mind. When you are ready, write about it in your own words.",
        "variations": [
            {"id": "happy_moment",
             "prompt": "Write about a happy moment in your life. What happened, "
                       "where were you, who was there, and how did it feel? "
                       "About 120–200 words."},
            {"id": "happy_achievement",
             "prompt": "Write about a time you felt proud or delighted about "
                       "something you achieved or received. What led up to it and "
                       "how did you feel? About 120–200 words."},
            {"id": "happy_people",
             "prompt": "Write about a joyful time you spent with people you care "
                       "about. What made it special? About 120–200 words."},
        ],
    },
    {
        "id": "sad",
        "title": "A sad moment",
        "difficulty": "Sad",
        "blurb": "A moment that made you sad. Choose one you are comfortable recalling.",
        "free_prompt": "Write about any sad moment. Go gently, take your time, and stop whenever you wish.",
        "ready_title": "Now, a sad moment",
        "ready_text": "Take a breath and be gentle with yourself. Choose a moment you are comfortable recalling; you can stop at any time.",
        "variations": [
            {"id": "sad_moment",
             "prompt": "Write about a sad moment in your life. What happened, "
                       "where were you, and how did it feel? About 120–200 words."},
            {"id": "sad_loss",
             "prompt": "Write about a time you felt disappointed, lonely or "
                       "missed someone. What was happening and how did you cope? "
                       "About 120–200 words."},
            {"id": "sad_change",
             "prompt": "Write about a change or goodbye that made you feel sad. "
                       "What did it mean to you? About 120–200 words."},
        ],
    },
]

# Neutral BASELINE passage written first by every participant. It is length-matched
# to the emotional passage so each person's emotional writing can be compared with
# their OWN neutral typing (within-person design; see affect.rhythm_shift).
BASELINE = {
    "id": "baseline", "title": "Baseline passage", "difficulty": "Baseline",
    "variations": [{"id": "baseline_room",
                    "prompt": "Describe the room you are in right now: the furniture, "
                              "the objects around you and how it is laid out. "
                              "About 120–200 words."}],
}

TASKS_BY_ID = {}
for _lvl in LEVELS + MOMENTS + [BASELINE]:
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
