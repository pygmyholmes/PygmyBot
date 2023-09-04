
from functools import wraps

class EventManager(object):

    @staticmethod
    def trigger_event(name:str):
        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                self.event_manager.add_event(name)
                result = func(self, *args, **kwargs)
                self.event_manager.trigger(name, *args, **kwargs)
                return result
            return wrapper
        return decorator

    def __init__(self):
        self.events = dict[str, EventManager.Event]()
    
    def add_event(self, event_id:str):
        if event_id not in self.events:
            self.events[event_id] = EventManager.Event()

    def add_listener(self, event_id:str, event_listener:callable):
        self.add_event(event_id)
        self.events[event_id] += event_listener
    
    def remove_listener(self, event_id:str, event_listener:callable):
        self.add_event(event_id)
        self.events[event_id] -= event_listener
    
    def trigger(self, event_id:str, *args, **kwargs):
        print(f"triggering {event_id}")
        self.events[event_id].trigger(*args, **kwargs)
        print(f"triggered {event_id}")

    class Event:
        def __init__(self):
            self.listeners = []
        
        def __iadd__(self, listener):
            self.listeners.append(listener)
            return self
        
        def __isub__(self, listener):
            if listener in self.listeners:
                self.listeners.remove(listener)
            return self

        def trigger(self, *args, **kwargs):
            for listener in self.listeners:
                listener(*args, **kwargs)