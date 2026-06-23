const OPTIONS = [
  { value: "", label: "All departments" },
  { value: "HR", label: "HR" },
  { value: "Engineering", label: "Engineering" },
  { value: "Sales", label: "Sales" },
];

export default function DepartmentFilter({ value, onChange }) {
  return (
    <div className="dept-filter">
      <label className="dept-filter-label" htmlFor="dept-select">
        Search scope
      </label>
      <select
        id="dept-select"
        className="dept-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {OPTIONS.map((o) => (
          <option key={o.value || "all"} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
