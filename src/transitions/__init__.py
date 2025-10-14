from __future__ import annotations

from typing import Protocol

from .slide import SlideTransition


class Transition(Protocol):
	def render(self, frame1, frame2, progress: float, **kwargs):
		...


def create_transition(name: str, **kwargs) -> Transition:
	"""Factory limited to slide transition in this project setup."""
	key = (name or '').strip().lower()
	if key in ('slide', 'slide-down', 'slide_up', 'slide-up'):
		direction = kwargs.pop('direction', 'down')
		return SlideTransition(direction=direction)
	# default to slide
	return SlideTransition(direction=kwargs.get('direction', 'down'))


__all__ = [
	'Transition',
	'create_transition',
	'SlideTransition',
]