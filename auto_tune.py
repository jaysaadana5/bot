def clamp(val, min_v, max_v):
    return max(min_v, min(val, max_v))


def adjust_threshold(config, increase=True):
    step = config.THRESHOLD_STEP
    new_val = config.THRESHOLD + step if increase else config.THRESHOLD - step
    config.THRESHOLD = clamp(new_val, config.MIN_THRESHOLD, config.MAX_THRESHOLD)


class AutoTuneManager:

    def __init__(self):
        self.last_tuned_cycle = -10
        self.current_cycle = 0

    def can_tune(self, config):
        return (self.current_cycle - self.last_tuned_cycle) >= config.TUNE_COOLDOWN_CYCLES

    def mark_tuned(self):
        self.last_tuned_cycle = self.current_cycle

    def next_cycle(self):
        self.current_cycle += 1


def should_tune(trades):
    losses = [t for t in trades if t["profit"] < 0][-5:]

    if len(losses) < 3:
        return False

    avg_loss = sum(abs(t["profit"]) for t in losses) / len(losses)
    return avg_loss > 8
