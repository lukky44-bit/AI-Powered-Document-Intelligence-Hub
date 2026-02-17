import Sidebar from "../components/Sidebar";
import FileUpload from "../components/FileUpload";
import RagQuery from "../components/RagQuery";

export default function Dashboard() {
  return (
    <div style={styles.container}>
      {/* Sidebar */}
      <div style={styles.sidebar}>
        <Sidebar />
      </div>

      {/* Main content */}
      <div style={styles.main}>
        <h2>📄 Document AI Hub</h2>

        <FileUpload />
        <hr />
        <RagQuery />
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: "flex",
    height: "100vh",
  },
  sidebar: {
    width: "280px",
    borderRight: "1px solid #ddd",
    padding: "16px",
    overflowY: "auto",
  },
  main: {
    flex: 1,
    padding: "24px",
    overflowY: "auto",
  },
};
