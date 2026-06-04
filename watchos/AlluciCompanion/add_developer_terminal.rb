require 'xcodeproj'

project_path = '/Users/alluci/Downloads/alluci-sovereign-agent-main/watchos/AlluciCompanion/AlluciCompanion.xcodeproj'
project = Xcodeproj::Project.open(project_path)

target = project.targets.find { |t| t.name == 'AlluciCompanion' }
views_group = project.main_group.find_subpath('AlluciCompanion/Views', true)

file_path = 'AlluciCompanion/Views/DeveloperTerminalView.swift'

unless views_group.files.any? { |f| f.path == 'DeveloperTerminalView.swift' }
  file_ref = views_group.new_file('DeveloperTerminalView.swift')
  target.add_file_references([file_ref])
  project.save
  puts "Added DeveloperTerminalView.swift to target"
else
  puts "DeveloperTerminalView.swift already exists in target"
end
