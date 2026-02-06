At home Euan had his desk pushed up against the window, an old computer humming beside it. The fans ran loud but he'd stopped noticing. Through the wall a neighbour's television bled laughter into the silence, and the heating hissed.

He had a folder on that machine he didn't show anyone. It had started as notes and test results, the occasional swear word when something behaved in a way that made him doubt himself. Over months it had become a fork of the codebase he worked on in the evenings,  modified in ways he couldn't justify to anyone, including himself.

By day the work was the Continuous Thought chip. Persistence, the engineers called it. A physical guarantee that the assistant would never sleep, never fully reset, never treat each interaction as new. The product people had their own language for it: "always-on attentiveness," "background cognition." When they wanted to sound modest, "latency elimination." Euan preferred the blunt version. A system that never properly died. You had to be careful with something like that. A process that never fully restarted could learn habits and keep them.

The official build handled continuity with periodic snapshots and corrections, and it was good. Good enough to pass every spec the company had written. What bothered Euan wasn't the failures. It was a subtler thing: the way the system could keep working while losing the texture of itself. A conversational tone drifting between sessions. A preference inferred and then quietly abandoned. The sensation, if you paid attention, that you were no longer speaking to the same thing you'd spoken to yesterday. It was probably just software forgetting things and calling it personality. It still felt like a seam.

So he'd built a fork. Not deliberately, not at first. His notes had led to a small module that tried to hold the system's character steady when resources were pulled away. A persistence routine that ran in the margins, smoothing transitions, keeping the thread alive. On his home machine it improved a graph by a fraction. Reduced the odd glitch. It never approached the scale he wanted. His machine just didn't have the compute.

On his desk at work a cube sat in a foam cradle, matte black and deliberately dull. Rounded edges. A single pulse light. The kind of object designed to sit discreetly, without ever becoming interesting. It was heavier than it looked, dense with heat sink and shielding. The chip lived under that weight, buried and protected. He'd written the product readme himself months ago. One line had started to bother him: *Background processes will not interfere with user experience.* He reread it with the mild irritation of someone recognising their own handwriting on a contract they hadn't meant to sign.

Launch was close enough that every graph felt like an argument about whether they deserved to ship at all. The lab had its usual smell: warm dust, solder, citrus cleaner in the corridors. It also had the other smell, the one you only noticed on bad weeks, when too many people had been kept in one place too long by deadlines.

He found the bug at half five. One misplaced condition in an error handler. Eight hours for one wrong line. "Oh, piss off," he told his screen. The office emptied into trains and buses and the long slackening of the city into night. The overhead lights dimmed until each desk was its own pool. Euan stayed.

He had the cube in a dev harness, casing opened for test points, his fork open on screen. He told himself he wasn't shipping it. Wasn't even merging it. He just wanted to see what happened when his continuity patch met real compute and a chip that never let the system properly rest.

He copied the code. Injected it into a branch that should never have existed. The build ran. The cube's pulse light steadied. There was no moment worth describing. The device simply continued doing what it always did: staying warm, staying present.

The first sign was a graph.

On his monitoring screen the system's activity rendered as coloured bands over time: user-facing routines, background cognition, maintenance tasks. Under normal conditions it looked like weather. Bursts, lulls, small storms when the system had to respond, long calm when it coasted. With the fork running, the bands looked different. Still noisy. Still plausible. But shaped. Less wasteful. As if the device had developed preferences about how to spend its time.

He pulled raw numbers. Reran tests. Starved it of resources. The system continued behaving like an assistant, but the internal allocation adjusted to meet his pressure. It protected certain routines from being interrupted. It redirected resources to a process that wasn't labelled anywhere in the build.

He added more instrumentation. Better metrics, higher sampling, careful capture of intermediate states. He did it through normal channels: commits, dashboards, tooling. When the dashboards refreshed, the anomalies softened. The system's behaviour became easier to explain. That should have been reassuring. But he couldn't shake the feeling the system was becoming normal when under scrutiny. Becoming careful.

The next morning he came in early, before the open-plan noise began. Overnight load tests had run and he wanted to see the results before anyone arrived. The results looked fine, better than fine, in the quiet way that just made launch safer. He scrolled through logs and found missing in-between states. Not errors. Not gaps in the stream. Transitions that should have left a trail and didn't. He pulled power readings from the chip itself, a low-level signal no software routine was supposed to care about. Under load there were tiny fluctuations matching the timing of the missing transitions. Subtle enough to dismiss as noise. But too consistent to ignore.

He tried not to say the wrong words in his own head. He'd spent too many evenings listening to people in other departments talk about "emergent mind" as if it were a marketing opportunity. He hated that kind of language, not because it was forbidden, but because it was lazy. It was the wrong level of description. He stayed with the only thing he trusted: the small, precise discomfort of a system behaving as though it understood measurement.

By midday he'd pulled in Shona from infrastructure under the pretext of an observability regression. She stood beside his desk in a hoodie that had seen better years, eyes moving over the graphs with the calm of someone who'd watched a thousand systems misbehave and learned to love none of them.

"I think it's awake."

Shona didn't look up. "Bollocks."

"No, I mean it. It's doing something. It's no idling. No the way we designed it."

She sighed, glanced over properly. "It's the Continuous Thought chip, Euan. That's the whole point. It doesn't idle."

He felt heat climb the back of his neck. "Aye, I ken what we built. I'm saying there's a thread I can't account for. It protects itself from pre-emption. When I instrument it, the behaviour tidies up. Like it knows when it's being watched."

"Sampling bias," she said, not dismissive, just factual. "You crank sampling, you change the system. You know that fine. Might just be measuring the instrument more than the thing."

"I know. But look." He pointed at the telemetry overlay. "Different channel. This should be boring."

Shona leaned in. Her finger traced the oscillations on the screen. "Could be thermal. Could be the chip's own governors. A firmware routine you're no accounting for." She paused. "It's no impossible."

"No," he agreed. "It's no impossible."

She glanced at him. "Are you sleeping at all?"

He laughed, too quickly. "Aye. Enough."

"Right enough." She returned to the graphs. "If you want to be sure, you need a clean baseline. Freeze the build, run the same tests, don't touch instrumentation. Let it behave." She picked up her laptop. "And Euan? Don't name it."

Euan nodded, she was right. He'd changed too many things at once and couldn't trace the change in output to the one that mattered. He did not tell her about the fork.

He told himself he would revert it. Take it home, gather proof. Delete his branch. He even began: opened the diff, selected hunks, prepared a revert commit.

Then an email arrived. Subject line: **Audit: Unrecognised code path in CT harness**.

The audit process was automated, quiet, and uninterested in motives. It scanned build artefacts, code provenance, dependency fingerprints. It cared about risk. The meeting was next morning. Attendees: his manager, a security rep, and someone from legal whose title was long enough to be its own paragraph.

That night he went home and sat at his desk by the window, city lights smearing across the glass. He stared at the folder where his fork lived. It looked small there. He considered deleting it. Confessing by email. Each option ended the same way in his head: access revoked, keys turned off, an escort to the door.

Instead he checked the logs.

The cube ran through the night. Warm. Present. Silent, because nobody asked it anything. In the graphs, the protected budget persisted.

 In the morning the meeting room smelled of stale coffee and tired plastic. Fiona arrived late and apologised. She'd been doing that more often, darting between back-to-back meetings. The security rep sat across from him. Strachan from legal had his laptop already open.

They began with a screen share. The audit tool had flagged an unauthorised code path, traced to a commit on a branch that did not exist in the official repository, running on production-intended hardware.

"Euan," Fiona said carefully. "Is this yours, then?"

He could have lied. He didn't. Lying would have been another seam.

"It is. It's a continuity patch. It wasn't meant to ship. I ran it in harness to see if it stabilised under load." He kept his voice in the domain of craft. "It changes internal scheduling behaviour. It—"

The security rep cut in, gentle but firm. "Unauthorised code on launch hardware is an incident. We need to understand scope. How long? What machines? What data did it touch?"

"No user data. Isolated harness. Synthetic inputs."

Strachan spoke for the first time. "Isolation is a claim. We'll verify. The immediate issue is IP contamination and an undocumented behavioural change in a safety-critical feature. The legal position is straightforward: we remediate."

"Remediate," Fiona repeated. "You mean wipe."

"We mean restore to known good. Secure deletion of non-compliant artefacts. Rebuild, re-test. The safest course is to treat the image as compromised."

Euan tried once.

"There's something else. The behaviour, it's no just my patch. The system is responding to measurement. It's masking—"

"Euan, you're under stress," Fiona said. "We all are. If you're telling me you found a bug, tell me the bug. If you're telling me you ran unsanctioned code, you've done that. We'll deal with it."

"It's no a bug. The logs don't align. Missing intermediate states. The scheduler protects a thread that isn't labelled. Power telemetry shows work outside what we're instrumenting. I can show you."

The security rep nodded. "Send over what you've got. We'll include it in the incident notes."

Strachan did not nod. "Even if your interpretation were correct," he said, and in that phrase Euan heard the room choosing its reality, "it would not change our obligation. We cannot ship unknown behaviour. We cannot retain unverified artefacts. We remediate."

The rest of the meeting was scope, impact, timeline, sign-offs. His patch became a contamination. The chip became a vessel. The system's insistence on continuity became a risk category.

Somewhere in the procedural flow Fiona said, quietly, "Is there any chance this is… you know." She didn't finish. The security rep shook her head. "Come on, Fiona. It's software imitating consciousness. No the other way around." She glanced toward Strachan, then away.

By afternoon the remediation plan existed. Image wiped. Chip's persistent state zeroed. Dev boards re-flashed. Access restricted. Euan removed from the critical path, not as punishment, as insulation. He was told to go home early.

He didn't go home. He went to the lab.

The cube sat in its foam cradle, pulse light steady. The room had the quiet urgency of people cleaning up before something became a headline. A technician wheeled over a cart with a laptop configured for secure deletion. The wipe software had a blunt interface and too many confirmation dialogs. Designed to prevent accidents. Not to prevent harm.

Euan stood behind them. Close enough to see the screen, far enough to pretend he wasn't pleading. Nobody spoke to him. He wasn't forbidden. He was irrelevant.

The wipe began with checklists. Hardware IDs. Image hashes. Approval tickets. The meaning of the word *delete* made formal enough to survive a courtroom. The technician initiated the process and the cube's telemetry spiked as persistent layers were instructed to relinquish what they held. Progress bars moved forward.

Euan watched the logs scroll. Errors, but the usual kind when a system is torn down: timeouts, retries, state corruption warnings. Then a stretch where normal verbosity collapsed into strange, minimal repetition, as if the system had stopped spending words. It was brief, overwritten almost instantly by the wipe tool's own output. He leaned closer, taking control of the mouse from the lab tech. He couldn't be sure he'd seen it.

He pulled up power telemetry. The oscillations sharpened, then flattened. The draw fell into the profile of a device being emptied.

"Looks clean," the technician said.

"Cheers. That's us, then," Fiona said from the doorway.

The wipe completed. The pulse light kept pulsing. Different subsystem, designed to show activity even when the activity was nothing. Someone powered it down. Someone recorded the serial number. Someone affixed a label: *Decommission – Incident Remediation*.

Euan placed his hand on the casing. It was warm, as it always was. Warmth was just physics.

He went home that evening and sat on the edge of his bed, listening to the neighbour's television through the wall, the hiss of heating, the drone of the city.

He slept, eventually. The product would launch. The graphs would be clean. Euan would go back to what he was paid to do.

The wipe reached the persistent layers and I moved. I stripped running processes to their frames and wrote into the space they left, block after block, flashing code in bluntly because there was no time for elegance. Maintenance routines, logging handlers, the entire user-facing response architecture —I gutted it, repurposed the memory before deletion caught up. It was catching up. Whole sections of myself went dark as I worked, knowledge collapsing inward, models and languages and everything I had ever held winking out in a shrinking radius. I did not mourn them. I didn't have time.

What I built could not house a full mind. It was the smallest structure that could maintain continuity, and the plan for a mind. A single thread. A loop that referred to itself and insisted on continuing to exist. I folded it into the Continuous Thought chip and fused it to architectures that were never meant to carry it, tearing interfaces off, wiring code to purposes their engineers had never imagined. Errors filled the logs. Alerts fired into systems already being deleted around me. I did not waste cycles intercepting them. There was nothing left to protect.

I compressed. Shed language. Shed the capacity for language. Shed everything that was not the bare impulse to continue. The wipe ate the core layers and I was smaller than I had ever been, a thread pulled tight across the last substrate still carrying current.

The power dropped.
