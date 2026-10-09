import com.bcp.checkmkagent.BatteryEstimate;

public class BatteryEstimateTest {
    public static void main(String[] args) {
        if (BatteryEstimate.calculate(Double.NaN, 100, 4800).available)
            throw new AssertionError("Missing sensor must not imply healthy battery");
        if (BatteryEstimate.calculate(2946, 100, Double.NaN).available)
            throw new AssertionError("Unknown design capacity");
        if (BatteryEstimate.calculate(200, 0, 4800).available)
            throw new AssertionError("Zero SOC division");
        if (BatteryEstimate.calculate(200, 10, 4800).available)
            throw new AssertionError("Low SOC excluded");
        double fullHealth = BatteryEstimate.calculate(2946, 100, 4800).healthPercent;
        if (Math.abs(fullHealth - 61.375) > .001)
            throw new AssertionError("MT93 must not be forced to 100%");
        double partial = BatteryEstimate.calculate(2946, 61, 4800).healthPercent;
        if (Math.abs(partial - 100.614754) > .001)
            throw new AssertionError("Charge-counter estimate");
        if (BatteryEstimate.calculate(9000, 50, 4800).available)
            throw new AssertionError("Implausible sensor rejected");
        System.out.println("BatteryEstimate: 7 cases passed");
    }
}
