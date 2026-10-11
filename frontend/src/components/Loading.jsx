export function Spinner({ size = 18 }) {
  return <span className="spinner" style={{ width: size, height: size }} />;
}

export function PageLoading({ label = "Loading..." }) {
  return (
    <div className="page-loading-state">
      <Spinner size={22} />
      <span>{label}</span>
    </div>
  );
}
