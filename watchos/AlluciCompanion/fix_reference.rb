require 'xcodeproj'

project_path = '/Users/alluci/Downloads/alluci-sovereign-agent-main/watchos/AlluciCompanion/AlluciCompanion.xcodeproj'
project = Xcodeproj::Project.open(project_path)

views_group = project.main_group.find_subpath('AlluciCompanion/Views', true)

# Find any incorrect references and remove them
views_group.files.each do |f|
  if f.path == 'DeveloperTerminalView.swift'
    f.remove_from_project
  end
end

# Re-add with explicit relative path
file_ref = views_group.new_file('Views/DeveloperTerminalView.swift')
file_ref.set_path('Views/DeveloperTerminalView.swift')
file_ref.source_tree = '<group>'

target = project.targets.find { |t| t.name == 'AlluciCompanion' }
target.add_file_references([file_ref])
project.save

puts "Fixed reference."
