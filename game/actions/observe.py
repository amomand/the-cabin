"""Authored visual and acoustic attention on the shared engine path."""
from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult
from game.story import perception
from game.story.targeted_attention import observe_target


class LookAction(Action):
    @property
    def name(self) -> str:
        return "look"

    def execute(self, ctx: ActionContext) -> ActionResult:
        target = ctx.args.get("target") or ctx.args.get("item")
        if target:
            return ActionResult.authored(observe_target(ctx, "look", target))
        text = perception.look(ctx.room, ctx.player, ctx.world_state)
        text += ctx.room.get_items_description(ctx.world_state)
        attention = ctx.map.observe_current_room("look", ctx.player)
        if attention:
            text += "\n\n" + attention
        return ActionResult.authored(text)


class ListenAction(Action):
    @property
    def name(self) -> str:
        return "listen"

    def execute(self, ctx: ActionContext) -> ActionResult:
        target = ctx.args.get("target") or ctx.args.get("item")
        if target:
            return ActionResult.authored(observe_target(ctx, "listen", target))
        attention = ctx.map.observe_current_room("listen", ctx.player)
        return ActionResult.authored(attention or perception.listen(ctx.room, ctx.world_state))
