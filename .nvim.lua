-- Project-specific Telescope config
local ok, telescope = pcall(require, "telescope")
if not ok then return end

telescope.setup({
    defaults = {
        file_ignore_patterns = {
            "venv311/",
            "%.vtt",
            "%.mp4",
            "%.git/",
            "__pycache__/"
        },
    },
})
