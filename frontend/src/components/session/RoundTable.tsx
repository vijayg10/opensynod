import type { SeatConfig } from "@/types/api";

interface RoundTableProps {
  seats: SeatConfig[];
  currentSpeaker: string | null;
  size?: number;
}

const SEAT_COLORS = [
  "#6366f1", // indigo
  "#8b5cf6", // violet
  "#ec4899", // pink
  "#f59e0b", // amber
  "#10b981", // emerald
  "#3b82f6", // blue
  "#ef4444", // red
  "#14b8a6", // teal
];

// Label positions as [x%, y%, anchor] placed around the outside of each figure.
// anchor: "center" | "left" | "right" — controls text alignment relative to the point.
type LabelPos = [number, number, "center" | "left" | "right"];

const LABEL_POSITIONS: Record<number, LabelPos[]> = {
  2: [
    [51, 8, "center"],   // 12 o'clock
    [51, 68, "center"],   // 6 o'clock
  ],
  3: [
    [46, 74, "center"],   // 6 o'clock
    [14, 35, "right"],    // 10 o'clock
    [58, 12, "left"],     // 1 o'clock
  ],
  4: [
    [51, 78, "center"],   // 6 o'clock
    [16, 40, "right"],    // 9 o'clock
    [51, 8, "center"],   // 12 o'clock
    [86, 40, "left"],     // 3 o'clock
  ],
  5: [
    [52, 8, "center"],   // 12 o'clock
    [16, 40, "right"],    // 8 o'clock
    [52, 80, "center"],   // 6 o'clock
    [87, 40, "left"],     // 2 o'clock — beside upper-right figure's shoulder
    [-5, 65, "left"],     // 4 o'clock — beside right figure
  ],
  6: [
    [46, 76, "center"],   // 6 o'clock
    [16, 48, "right"],    // 8 o'clock
    [16, 24, "right"],    // 10 o'clock
    [50, 10, "center"],   // 12 o'clock
    [82, 22, "left"],     // 2 o'clock
    [84, 44, "left"],     // 4 o'clock
  ],
  7: [
    [46, 78, "center"],   // 6 o'clock
    [16, 50, "right"],    // 7:30
    [14, 28, "right"],    // 9:30
    [28, 14, "right"],    // 11 o'clock
    [72, 12, "left"],     // 1 o'clock
    [86, 28, "left"],     // 2:30
    [86, 50, "left"],     // 4:30
  ],
  8: [
    [46, 78, "center"],   // 6 o'clock
    [16, 52, "right"],    // 7:30
    [12, 32, "right"],    // 9 o'clock
    [22, 16, "right"],    // 10:30
    [52, 8, "center"],    // 12 o'clock
    [78, 16, "left"],     // 1:30
    [88, 32, "left"],     // 3 o'clock
    [86, 52, "left"],     // 4:30
  ],
};

export function RoundTable({ seats, currentSpeaker, size = 420 }: RoundTableProps) {
  const count = Math.max(2, Math.min(8, seats.length));
  const imageSrc = `/table-images/${count}-people.png`;
  const positions = LABEL_POSITIONS[count] ?? LABEL_POSITIONS[4];

  return (
    <div
      className="relative select-none"
      style={{ width: size, height: size * 0.796 }}
      aria-label="Round table seating layout"
    >
      <img
        src={imageSrc}
        alt={`${count} people at a round table`}
        className="w-full h-full object-contain"
        draggable={false}
        style={{
          maskImage: "radial-gradient(ellipse 59% 55% at 50% 48%, black 38%, transparent 92%)",
          WebkitMaskImage: "radial-gradient(ellipse 59% 55% at 50% 48%, black 38%, transparent 92%)",
        }}
      />

      {seats.slice(0, count).map((seat, i) => {
        const pos = positions[i] ?? [50, 50, "center" as const];
        const [xPct, yPct, anchor] = pos;
        const color = SEAT_COLORS[i % SEAT_COLORS.length];
        const isSpeaking = seat.seat_id === currentSpeaker;

        const translateX =
          anchor === "right" ? "-100%" : anchor === "left" ? "0%" : "-50%";

        return (
          <div
            key={seat.seat_id}
            className="absolute -translate-y-1/2 flex flex-col items-center pointer-events-none"
            style={{
              left: `${xPct}%`,
              top: `${yPct}%`,
              transform: `translate(${translateX}, -50%)`,
            }}
          >
            {/* Speaking pulse ring */}
            {isSpeaking && (
              <span
                className="absolute rounded-full animate-ping"
                style={{
                  width: "130%",
                  height: "130%",
                  border: `2px solid ${color}`,
                  opacity: 0.6,
                }}
              />
            )}

            {/* Name label */}
            <span
              className={`relative px-2.5 py-1 rounded-full text-white text-center whitespace-nowrap font-semibold leading-tight ${
                isSpeaking ? "animate-bounce-subtle" : ""
              }`}
              style={{
                fontSize: Math.max(10, size * 0.022),
                backgroundColor: color,
                boxShadow: isSpeaking
                  ? `0 0 12px 4px ${color}99, 0 0 24px 8px ${color}44`
                  : "none",
                transform: isSpeaking ? "scale(1.1)" : "scale(1)",
                transition: "transform 0.3s ease, box-shadow 0.3s ease",
              }}
            >
              {seat.display_name}
            </span>
          </div>
        );
      })}
    </div>
  );
}
