from datetime import datetime, timedelta


class RiskManager:

    def __init__(self):
        self.loss_streak = 0
        self.cooldown_end = None

    def in_cooldown(self):
        return self.cooldown_end is not None and datetime.utcnow() < self.cooldown_end

    def trigger_cooldown(self, hours):
        self.cooldown_end = datetime.utcnow() + timedelta(hours=hours)
        print(f"Cooldown started for {hours}h — resuming at {self.cooldown_end.strftime('%H:%M UTC')}")

    def update(self, profit, config):
        if profit < 0:
            self.loss_streak += 1
        else:
            self.loss_streak = 0

        if self.loss_streak >= config.MAX_LOSS_STREAK:
            self.trigger_cooldown(config.COOLDOWN_HOURS)
            self.loss_streak = 0
