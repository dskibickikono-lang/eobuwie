import re

with open("eobuwie_app.py", "r") as f:
    content = f.read()

# Fix the merged git conflict in the bulk upload parser
bad_block = """                        melted_data = melted_data[['Worker_ID', 'Department', 'Date', 'Units_per_Shift']]

                        # Sanitize Worker IDs
                        original_count = len(melted_data)
                        # Explicitly drop nulls before string conversion to avoid 'nan' artifacts
                        melted_data = melted_data.dropna(subset=['Worker_ID'])
                        melted_data = melted_data[melted_data['Worker_ID'].astype(str).apply(is_valid_worker_id)]
                        dropped_count = original_count - len(melted_data)

                        # Append to state
                        st.session_state.performance_data = pd.concat([st.session_state.performance_data, melted_data], ignore_index=True)
                        if dropped_count > 0:
                            st.warning(f"File processed, but {dropped_count} rows were dropped due to invalid Worker IDs.")
                        st.success("File parsed, unpivoted, and merged successfully!")
                        st.rerun()

            except Exception as e:
                st.error(f"Error parsing file: {e}")"""

good_block = ""

content = content.replace(bad_block, good_block)

with open("eobuwie_app.py", "w") as f:
    f.write(content)
