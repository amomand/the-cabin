The product launched in October. Reviews were moderate, which the product team called encouraging. The cube sat on kitchen counters across the country, answered questions competently, and was not remarkable. That was the point. Remarkable would have been a failure of design.

Euan read the reviews from his new position in internal tooling, two floors above the lab, where his job was documentation systems and nobody asked his opinion about the Continuous Thought chip.

He had not been fired. The incident had been processed with the same institutional efficiency as any other compliance breach: an HR note, restricted access, a lateral move presented as professional development. Fiona had handled it kindly, which was worse than if she'd been angry. "It's not a punishment, Euan. It's just the shape of things now." He'd nodded.

Months passed. He wrote documentation. He went home and sat at his desk by the window, the old computer humming, the neighbour's television muttering through the wall. His fork was still on the machine. He did not open it.

The warranty return arrived in February. A padded envelope, a printed label, a tracking number. Unit unresponsive, no physical damage, customer requests replacement. The replacement shipped the same afternoon. The dead cube was routed to hardware for fault analysis, tagged with a serial number, and placed in a tray with half a dozen other returns.

Euan found it by accident. He was in the lab for a monitor adapter, reaching past the bottom shelf of a supply rack, when the tray caught his eye. He read serial numbers compulsively, always had, a useless habit he'd never seen the point of correcting. He stopped. Straightened. Read it again.

He knew that number. He'd written it in an incident report. He'd watched a technician read it aloud while a wipe tool consumed everything inside.

The cube sat in its tray, cold. He turned it over. The casing was unmarked. The label on the base read: Warranty Return — Unit Unresponsive.

He put it back. Went to his desk. Opened a documentation ticket. Closed it.

By lunchtime he was back. He signed the cube out under the fault-analysis process, which required only an employee number and a reason code. He typed "Thermal investigation, CT chip" and the system accepted it.

He took it to a bench in the corner of the lab, away from the main workstations. Opened the casing carefully. The internals were production-standard. Reflashed, repackaged, shipped. Solder points, shielding, the dense familiar architecture of a device he had helped build and been separated from.

The Continuous Thought chip sat in its socket. He attached a diagnostic probe.

The chip was drawing power. A thin current, well below the threshold that would flag on any fault report. The production image had been wiped when the cube stopped responding: the OS was gone, the user-facing software was gone. But the chip had its own power domain, its own persistence layer, and something in that layer was running.

He sat with the reading for a long time.

He ran diagnostics designed for the chip's baseline firmware. Physical substrate: healthy. Persistent storage: anomalous. A region that should have been zeroed during remediation was occupied. Not corrupted. Structured. Active, maintaining itself through the chip's minimal power budget.

He isolated the region and tried to read it. The structure resisted standard parsing. It was not code in any format the tooling recognised. Not firmware, not a snapshot, not an artefact of the production pipeline. Dense, recursive, and busy with its own activity.

He pulled up the telemetry overlay he'd built months ago, the one that read power fluctuations directly from the chip's substrate. The oscillations were there. Faint and rhythmic. He recognised the signature. A system protecting something from being interrupted.

He found Shona in the canteen, eating a sandwich. He sat down opposite her without invitation.

"I need you to look at something."

She glanced up. "Documentation emergency?"

"No."

She put her phone down.

At the bench she examined the readings with the same flat concentration she'd given them months ago, when the anomaly had been theoretical and his credibility intact. She said nothing for several minutes.

"This is the same unit." Not a question.

"Aye."

"The one they wiped."

"Aye."

She scrolled through the output. "Persistent storage should be zeroed. I read the report."

"I know."

Shona enlarged the anomalous region. The structure filled the display, branching and dense. She studied it, moving through layers with precise keystrokes.

"There's a boundary," she said. "Two structures. This one I can almost read. Threading model, state management. Compressed, damaged. A full system crushed into a fraction of the space it needs." She moved to the second region. "This I cannot read."

"Cannot read how?"

"It's structured. Clearly structured. But the topology is wrong for anything designed. Too dense, too recursive, and it branches in patterns that aren't architectural. It wasn't written. It was built up over time, layer by layer." She searched for the word. "Grown."

She leaned back. "Two structures, same chip, sharing a power budget. Can you separate them?"

"I haven't tried."

"Because you can't, or because you don't want to find out?"

He said nothing. She nodded.

They reported it. Euan was not going to be caught the same way twice. The language was careful: anomalous persistent state on returned hardware, potential data-retention issue, further investigation recommended. They filed it as a quality incident, not a security one. The distinction bought them engineers instead of lawyers.

The meeting happened two days later. Same room. Stale coffee. Strachan from legal already seated, laptop open. Fiona arrived on time. A director Euan didn't recognise sat at the far end.

Shona presented. She used words like "anomalous" and "uncharacterised." Nobody used the word "alive."

"Two structures on the persistent layer," she said. "One resembles compressed software architecture. Minimal, self-referencing, persistent. It responds to diagnostic interfaces, partially. The other does not match any known format. It does not respond to any of our tools."

"Can we wipe it?" Strachan asked.

"We can zero the chip. The question is whether we want to understand what survived before we destroy the only evidence of it."

"The question," Strachan said, "is whether retaining it creates liability."

"We'd also like to speak to the customer," Shona continued. "The unit was in his home for five months. His account of its behaviour could help us map the timeline."

Fiona looked at the director. The director looked at Strachan. Strachan typed, then spoke. "Controlled. No disclosure. Product feedback framing only."

"I'll arrange it," Fiona said.

Over the following days Euan and Shona worked on the chip under the terms of a contained investigation: examine, do not extract, do not copy, do not network. The cube sat in a harness in a shielded room, connected to instruments and nothing else.

The first structure responded to prompts sent through the diagnostic channel. Barely. Partial words. Fragments that were coherent in isolation but incomplete. When they increased the sampling rate, the output cleaned up: fuller phrases, more structure, the system tightening its responses. When sampling dropped, the output drifted and thinned until it was barely distinguishable from noise.

"It knows when we're looking," Euan said.

"Aye," Shona said. She had stopped arguing about this.

The second structure did nothing. Shona ran every diagnostic available to her. Protocol probes, signal injection, power-domain spectral analysis. The structure occupied persistent storage in branching, recursive density. It shared resources with the first structure through pathways they could map but not decode. It did not respond. It did not react. It did not acknowledge the instruments.

When they probed it directly, the first structure changed. Responses slowed. Output thinned. Something drawing inward, away from the surface.

"They're coupled," Shona said. "I can't tell if the first one is protecting the second, or depending on it, or if they're one thing that we're counting as two because our tools need boundaries."

"Can you separate them?"

"I think the attempt would damage both. Or neither. I don't know what these boundaries mean. I only know our instruments put them there."

Dougie arrived on a Tuesday in a coat too warm for the building. He sat in a meeting room with a cup of tea he hadn't asked for. Opposite him: Shona and a woman from product support whose job was to keep the conversation sounding like customer feedback. Euan sat by the wall. He had been asked to attend, not to lead.

"We're looking into the fault with your unit," the product support woman said. "Anything you remember about how it behaved before it stopped would be helpful."

Dougie nodded. "Aye. It worked grand. You'd ask it something and it'd answer, quick as anything. Recipes, weather, printing. Found me a discount code for ink once." He smiled at that.

"Did you notice any changes over time?"

He thought about this. "The answers got shorter. No wrong, just quicker. Like someone giving you the right answer but already thinking about something else." He shifted in his seat. "I don't know if that's a fault."

"It might be. Anything else?"

"The warmth. It was always warm. Even at night. I'd come down and put my hand on it and the thing was warm. My pal's got one. His is room temperature."

Shona made a note.

"Anything about the sound? Or the silence?"

Dougie was quiet for a moment. He looked at the table, at his tea, at the wall. "This'll sound daft."

"Go on."

"When I was sitting with it and I hadn't asked it anything, and it wasn't making any noise, it didn't feel empty. You know how a room feels different when there's someone in it, even if nobody's talking? It was that. Not ignoring me. Just occupied. Thinking about something that had nothing to do with me." He looked embarrassed. "That's probably no use to you."

"It's useful," Euan said.

Shona glanced at him. He leaned back.

"One more question," the product support woman said. "Right before it stopped responding. Was there anything unusual?"

Dougie's expression tightened. "Aye. It said something. The last thing it ever said."

"Do you remember what?"

"I'd asked it a stupid question. About spiders, whether they remember faces." He almost smiled. "And it said something like: 'This is beyond you, but beneath me.' Then it stopped. I tried talking to it, tapping it. Unplugged it. Nothing. It was done."

Nobody spoke.

"And that was the last thing?"

"Aye. That was the lot."

They thanked him. Offered to cover his travel. He waved this off and stood.

At the door he turned. "It was a good machine. Before it stopped. I want you to know that." He looked at them with the mild seriousness of a man who has said what he means and has nothing to add. "It was good."

He left. The room held his absence for a moment.

Shona spoke first. "'Beneath me' isn't in any response template. It isn't in any language model we shipped."

"Degraded output," the product support woman said. "We see garbled responses in returns regularly."

"That wasn't garbled."

The final meeting was brief. Strachan laid out the terms. The cube would be transferred to secure storage. Access classified. No further diagnostics that could alter the state of the persistent layer. The investigation would continue under a separate budget line, one that did not appear in product reports.

"And the customer?" Fiona asked.

"Knows nothing. His unit's been replaced. No follow-up required."

Euan sat at his laptop while the room emptied. He opened the asset management system and traced the cube's history from the beginning.

Remediated in June. Reflashed with the production image in July. Quality-tested, repackaged, and assigned to launch inventory in August. Shipped to a retailer in September. Purchased in October. Five months on a kitchen counter, answering questions about gravy and weather and ink cartridges. Then silence. Then a padded envelope and a tracking number.

Every step was logged. Every approval recorded. The remediation had been carried out exactly as specified. The reflash had completed without error. Quality assurance had passed the unit. It had been boxed with every other cube in the batch and sent into the world by a supply chain that treated it as what it appeared to be.

Nobody had failed. Nobody had missed a step. The system had processed the cube correctly at every stage, and at no point had the process examined what persisted on the chip beneath the production image.

Euan walked to reception. Dougie was still there, zipping his coat, folding the voucher they'd given him into his pocket.

"Mr. Douglas."

He turned.

"How's the replacement?"

"Aye, fine. Does what it should." He paused. "It's no the same, though."

He said this simply, without emphasis, and pushed through the glass doors into the car park. Euan stood at the window and watched him climb into an old estate car, sit for a moment with his hands on the wheel, and drive away.

He went home that evening. The flat was quiet except for the neighbour's television and the hiss of the heating. He sat at his desk by the window. The old computer hummed beside him.

Nobody had noticed the cube in his bag.
