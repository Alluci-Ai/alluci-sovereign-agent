require 'xcodeproj'

project_path = '/Users/alluci/Downloads/alluci-sovereign-agent-main/watchos/AlluciCompanion/AlluciCompanion.xcodeproj'
project = Xcodeproj::Project.open(project_path)
target = project.targets.find { |t| t.name == 'AlluciCompanion' }

managers_group = project.main_group.find_subpath('AlluciCompanion/Managers', true)
views_group = project.main_group.find_subpath('AlluciCompanion/Views', true)

# Remove existing references if any to avoid duplicates
managers_group.files.each { |f| f.remove_from_project if ['ContextRouter.swift', 'MultipeerSyncManager.swift', 'LocalInferenceManager.swift'].include?(f.path) }
views_group.files.each { |f| f.remove_from_project if f.path == 'PairingTransferView.swift' }

refs = []

# Add Managers
['ContextRouter.swift', 'MultipeerSyncManager.swift', 'LocalInferenceManager.swift'].each do |file|
  ref = managers_group.new_file("Managers/#{file}")
  ref.set_path("Managers/#{file}")
  ref.source_tree = '<group>'
  refs << ref
end

# Add View
ref = views_group.new_file('Views/PairingTransferView.swift')
ref.set_path('Views/PairingTransferView.swift')
ref.source_tree = '<group>'
refs << ref

target.add_file_references(refs)
project.save

puts "Added Phase 10 files to project"
