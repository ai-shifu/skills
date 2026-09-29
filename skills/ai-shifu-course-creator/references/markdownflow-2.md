# Writing for the 2.0 engine

The 1.0 spec in `markdownflow.md` still describes the notation. This describes what changes
when a course is taught by the 2.0 engine, and it is all drawn from lessons run on the
simulation environment rather than from the design.

Which engine teaches a course is a deployment setting, not something in the course. An author
cannot see it and does not choose it. **So write one script that works under both**: nothing
here asks for a different notation, only for habits that hold either way.

## What actually changed

In 1.0 the platform executed your script: it split it into blocks, expanded each one with the
model, and the model never saw the next block. In 2.0 the whole script goes to the model as its
task, and the model decides how to work through it.

That single difference is behind everything below.

### The script is read as instructions, not as a text to recite

It always was in 1.0 too, but 1.0's block boundaries hid a lot. In 2.0, a line like

> 讲一下阶地的形成，最好结合黄河的例子

is a brief, and the model writes the lesson from it. If you want particular words said, that is
what `===` is for.

### The model may now adapt, within limits

Since the rules were loosened, a lesson may ask something your script did not list, put a point
another way, or take a step in two turns, when the learner needs it. What it may **not** do is
add subject matter: no invented facts, examples or claims, and nothing borrowed from elsewhere
in the course. Anything it adds serves one of your steps rather than becoming a step of its own.

Practical effect: a script no longer has to spell out every follow-up. Writing the intent is
usually enough, and often better.

## Things worth writing differently

### Say where the lesson ends

The model is told to call `finish` when nothing in the script remains. It is reliable when the
script ends on something recognisable -- 「这一节到此结束」, a closing summary -- and much less
so when the script simply stops mid-topic. A lesson that does not finish stays open in the
learner's outline.

Measured: on a script whose last line was an explicit ending, the model finished on its first
turn in 18 of 20 runs.

### Put a limit on a retry, and expect to restate it

`如果答错，提示一次，最多两次` is honoured much of the time, and **not always**: in one
measurement 7 of 20 lessons kept asking past the limit. The host stops a runaway eventually, but
the learner has by then answered more times than you meant. Keep loops short and their exits
obvious.

### `---` divides, it does not pause

A separator ends a section. It does not make the learner press anything. If you want a pause,
ask for one in words -- 「看完上图再继续」 -- and the model will offer a button.

### Ask questions with `?[...]`, not in prose

A question typed as ordinary text is not a question the engine knows about. The host now
recognises one written into the narration and turns it into a real question, but it cannot
recover the variable, so the answer is not stored. Use the notation and name the variable.

### Options cannot contain `|`, `//`, `]` or a newline

The interaction grammar uses those as its own delimiters. An option carrying a URL
(`https://...`) or a regular expression (`^[a-z]+$`) breaks the question: the learner is shown
the prompt with no controls under it. Until this is fixed in the grammar, keep such things in
the surrounding text and let the options be short.

### Preserved content is preserved, markers are not shown

`===…===` and a `!===` fenced block reach the learner word for word, and the markers themselves
are never shown or read aloud. Use it for anything that must be exact: a definition, a quoted
question, a figure caption.

### Show the notation with a backslash

A lesson that teaches MarkdownFlow writes `\?[A | B]` to show the notation rather than use it.
Inside a fenced code block it is also left alone.

## Settings

| Setting | 2.0 |
|---|---|
| course model, temperature | used |
| **teaching brief** (`llm_system_prompt`, course/chapter/lesson) | used — nearest one wins, and only that one; they do not stack |
| **ask brief** (`ask_llm_system_prompt`) | **not used**: set it and nothing reads it |
| listen mode | used; the spoken track is the platform's, not the engine's |

The teaching brief is where audience and voice belong -- 「对象：高三学生」,「语气简明，不要展开
解释」. It shapes how a lesson is taught; it does not add to what is taught, and it cannot
override the engine's own rules.

## Two things that still bite

Both are known, both are being worked on, and a script can avoid them today.

1. **A lesson the model delivers in one turn without finishing stays open.** End the script on
   something that reads as an ending.
2. **An option containing `//` or `]` loses its controls.** Keep them out of options.
