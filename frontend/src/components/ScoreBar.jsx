export default function ScoreBar({ label, value }) {
  const color =
    value >= 80 ? 'from-leaf-600 to-emerald-400' : value >= 50 ? 'from-amber-500 to-yellow-400' : 'from-red-500 to-orange-400'
  return (
    <div className="rounded-xl border border-gray-100 bg-white/70 p-3">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium capitalize text-gray-600">{label}</span>
        <span className="font-bold text-gray-900">{value}</span>
      </div>
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-gray-100">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${color}`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  )
}