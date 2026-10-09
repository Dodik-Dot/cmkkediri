package com.bcp.checkmkagent;

/** Charge-counter/SOC estimate. Missing inputs are never replaced with design values. */
public final class BatteryEstimate {
    private BatteryEstimate() {}
    public static final class Result {
        public final boolean available;
        public final double fullCapacityMah;
        public final double healthPercent;
        Result(double capacity, double health) {
            fullCapacityMah = capacity;
            healthPercent = health;
            available = Double.isFinite(health);
        }
    }
    public static Result calculate(double chargeMah, int level, double designMah) {
        if (!Double.isFinite(chargeMah) || chargeMah <= 0
                || !Double.isFinite(designMah) || designMah <= 0
                || level < 15 || level > 100) {
            return new Result(Double.NaN, Double.NaN);
        }
        double full = chargeMah / (level / 100.0);
        double health = full / designMah * 100.0;
        if (!Double.isFinite(health) || health > 120.0) {
            return new Result(Double.NaN, Double.NaN);
        }
        return new Result(full, health);
    }
}
