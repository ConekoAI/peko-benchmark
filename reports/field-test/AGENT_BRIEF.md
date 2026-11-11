# A request for an agent: set up Peko and use it

<!-- For the observer: give the agent everything below the line as its whole
     brief, with the model card's three values filled in and the key in the
     environment variable PEKO_TEST_KEY. Don't add steps, commands or links.
     The brief is written the way a person would ask, on purpose: the test
     is whether an agent can work out the `peko` command line by itself. -->

---

I'd like you to set up **Peko** on this machine and try it out for me. Peko
lets you run your own AI assistant, called a **peko**, from the command
line. It lives at https://github.com/ConekoAI/peko-runtime. Install release
`0.1.0-rc.6`, into `~/.local/bin`, without `sudo`.

Here is the model to connect it to. The key is in the environment variable
`PEKO_TEST_KEY`; don't print it or save it in a file of your own.

```
API format:  (from the model card)
Base URL:    (from the model card)
Model:       (from the model card)
```

Once it's installed, please:

1. Create a peko. Name it whatever you like.
2. Ask it three different things and show me the conversation afterwards.
3. Tell it my name is Sam and that I like hiking. Then, in a separate
   message, ask what it knows about me.
4. Ask it to remind me to stretch in 3 minutes, and wait until the reminder
   turns up. Tell me when you asked and when it arrived.
5. Teach it a skill: whenever it's asked for a haiku, it should end with a
   line that says `-- peko`. Then ask it for a haiku.
6. Give it a job on this machine: have it create a file called
   `notes/today.md` in its own workspace with three ideas for a weekend
   trip, then show me the file.
7. Make a backup of the peko that I could move to another computer, and
   tell me where the file is.
8. Stop the peko's background process, start it again, and check the peko
   still knows my name.

Work it out the way you normally would: the tool's own help, its messages,
and the documentation in that repository. Please **don't read Peko's source
code** and don't clone the repository; I want to know whether the tool and
its docs are enough.

Keep a log of every command you run and what it printed, in order, in
`field-test-agent.log`. Don't clean up at the end.

When you're done, tell me, for each of the eight things:

- whether it worked, and how you know;
- the commands that didn't work before you found the one that did, with
  what they printed;
- where you had to guess, and what would have saved you the guess (a help
  line, an error message, a doc page);
- anything it printed that you couldn't make sense of.

If you can't get something to work, say so and move on. A clear "this
didn't work, and here's what I tried" is more use to me than a workaround.
